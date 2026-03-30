from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser


class GraderUtils:
    def __init__(self, llm):
        self.llm = llm

    def create_batch_retrieval_grader(self):
        """
        Grades ALL retrieved documents in a single LLM call.
        Returns a JSON array of scores for each document.
        """
        grade_prompt = PromptTemplate(
            template="""You are an evaluator determining which retrieved documents are relevant to a user's product search query.

You will receive a numbered list of documents and a user prompt. For EACH document, return "yes" if it contains information relevant to the user's needs (product mentions, recommendations, reviews, comparisons) or "no" if it is off-topic.

Return a JSON object with a single key "scores" containing an array of objects, each with "index" (the document number) and "relevant" ("yes" or "no"). No preamble or explanation.

User Prompt: {prompt}

Documents:
{resources}

Answer:""",
            input_variables=["resources", "prompt"],
        )
        return grade_prompt | self.llm | JsonOutputParser()

    def create_retrieval_grader(self):
        """Single-document grading fallback."""
        grade_prompt = PromptTemplate(
            template="""You are an evaluator determining whether a retrieved document is relevant to a user's product search query. Return a binary score "yes" or "no" in JSON with key "score".

Retrieved Document: {resources}
User Prompt: {prompt}

Answer:""",
            input_variables=["resources", "prompt"],
        )
        return grade_prompt | self.llm | JsonOutputParser()

    def create_hallucination_grader(self):
        """
        Checks if the generation is grounded in the retrieved documents.
        Returns JSON {"score": "yes"/"no"}.
        """
        hallucination_prompt = PromptTemplate(
            template="""You are a grader assessing whether product recommendations are grounded in the provided community discussions.

Check: Are the product names, features, and user experiences mentioned in the generation actually present in the source documents? If the generation invents products or testimonials not in the documents, score "no".

Return JSON with a single key "score" ("yes" if grounded, "no" if hallucinated). No preamble.

Source documents:
{documents}

Generation to check:
{generation}

Answer:""",
            input_variables=["generation", "documents"],
        )
        return hallucination_prompt | self.llm | JsonOutputParser()

    def create_answer_quality_evaluator(self):
        """
        Checks if the generation actually answers the user's question with useful recommendations.
        Returns JSON {"score": "yes"/"no", "feedback": "..."}.
        """
        eval_prompt = PromptTemplate(
            template="""You are an evaluator assessing whether a product recommendation response adequately answers the user's question.

Check:
1. Does the response recommend specific products (not vague categories)?
2. Are the recommendations relevant to what the user asked for?
3. Does the response include enough detail to be useful (reasons, pros/cons)?

Return JSON with "score" ("yes" if the response is useful, "no" if not) and "feedback" (brief explanation). No preamble.

User question: {input}
Source documents: {documents}
Generated response: {generation}

Answer:""",
            input_variables=["generation", "input", "documents"],
        )
        return eval_prompt | self.llm | JsonOutputParser()

    def create_question_rewriter(self):
        """
        Rewrites a vague user query into a more specific product search query.
        """
        rewrite_prompt = PromptTemplate(
            template="""You are a search query optimizer for a product recommendation system. Rewrite the following question to be more specific and searchable. Add relevant product category terms, use cases, and price range if implied.

Original question: {question}

Rewritten question (just the query, nothing else):""",
            input_variables=["question"],
        )
        return rewrite_prompt | self.llm | StrOutputParser()
