import json
from backend.agent.graph import GraphState


class GraphEdges:
    def __init__(self, hallucination_grader, answer_quality_evaluator):
        self.hallucination_grader = hallucination_grader
        self.answer_quality_evaluator = answer_quality_evaluator

    def post_grade_decision(self, state: GraphState):
        """After grading docs, decide: enough relevant docs or need to rewrite query."""
        resources = state.get("resources", [])
        perform_web_search = state.get("perform_web_search", False)

        if len(resources) < 1 or perform_web_search:
            print("---DECISION: DOCS IRRELEVANT, REWRITING QUERY---")
            return "irrelevant"
        else:
            print("---DECISION: DOCS RELEVANT, PROCEEDING---")
            return "relevant"

    def post_generation_check(self, state: GraphState):
        """After generation, check hallucination and answer quality."""
        print("---CHECK HALLUCINATIONS & ANSWER QUALITY---")
        prompt = state["prompt"]
        resources = [r.page_content if hasattr(r, "page_content") else str(r) for r in state.get("resources", [])]
        generation = state["generation"]

        # Serialize generation for grading
        if hasattr(generation, "model_dump"):
            gen_text = json.dumps(generation.model_dump(mode="json"))
        else:
            gen_text = str(generation)

        resources_text = "\n".join(resources[:5])

        # Check hallucination: is the generation grounded in the documents?
        try:
            hallucination_score = self.hallucination_grader.invoke({
                "documents": resources_text,
                "generation": gen_text
            })
            is_grounded = hallucination_score.get("score", "yes").lower() == "yes"
        except Exception as e:
            print(f"Hallucination check failed: {e}")
            is_grounded = True  # Default to grounded on error

        if not is_grounded:
            retry_count = state.get("retry_count", 0)
            if retry_count < 1:
                print("---DECISION: NOT GROUNDED, RETRYING GENERATION---")
                return "retry"
            else:
                print("---DECISION: NOT GROUNDED BUT MAX RETRIES, CONTINUING---")
                return "accept"

        # Check answer quality: does the generation answer the question?
        try:
            quality_score = self.answer_quality_evaluator.invoke({
                "input": prompt,
                "generation": gen_text,
                "documents": resources_text
            })
            answers_question = quality_score.get("score", "yes").lower() == "yes"
        except Exception as e:
            print(f"Quality check failed: {e}")
            answers_question = True

        if not answers_question:
            retry_count = state.get("retry_count", 0)
            if retry_count < 1:
                print("---DECISION: DOESN'T ANSWER QUESTION, RETRYING---")
                return "retry"

        print("---DECISION: GENERATION IS GOOD, PROCEEDING TO ENRICHMENT---")
        return "accept"
