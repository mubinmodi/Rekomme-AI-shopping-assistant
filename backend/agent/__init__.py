from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from backend.agent.edges import GraphEdges
from backend.agent.grader import GraderUtils
from backend.agent.graph import GraphState
from backend.agent.nodes import GraphNodes
from backend.agent.vector_store import get_pinecone_vector_store, Retriever
from backend.config import settings
from backend.utils import get_tavily_web_search_tool, get_tavily_basic_search_tool


def compile_graph():
    # Vector Store
    _vector_store = get_pinecone_vector_store()
    retriever = Retriever(vector_store=_vector_store)

    # LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, openai_api_key=settings.OPENAI_API_KEY)

    # Graders
    grader = GraderUtils(llm=llm)
    batch_retrieval_grader = grader.create_batch_retrieval_grader()
    hallucination_grader = grader.create_hallucination_grader()
    answer_quality_evaluator = grader.create_answer_quality_evaluator()
    question_rewriter = grader.create_question_rewriter()

    # Tools
    web_search_tool = get_tavily_web_search_tool()
    enrichment_search_tool = get_tavily_basic_search_tool()

    # Nodes
    graph_nodes = GraphNodes(
        llm=llm,
        retriever=retriever,
        batch_retrieval_grader=batch_retrieval_grader,
        question_rewriter=question_rewriter,
        web_search_tool=web_search_tool,
        enrichment_search_tool=enrichment_search_tool,
    )

    # Edges
    graph_edges = GraphEdges(
        hallucination_grader=hallucination_grader,
        answer_quality_evaluator=answer_quality_evaluator,
    )

    # Build workflow
    workflow = StateGraph(GraphState)

    # Register all nodes
    workflow.add_node("vector_search", graph_nodes.vector_store_retrieve)
    workflow.add_node("batch_grade", graph_nodes.batch_grade_documents)
    workflow.add_node("transform_query", graph_nodes.transform_query)
    workflow.add_node("web_search", graph_nodes.web_search)
    workflow.add_node("live_reddit_search", graph_nodes.live_reddit_search)
    workflow.add_node("generate", graph_nodes.generate)
    workflow.add_node("enrich_with_sources", graph_nodes.enrich_with_sources)

    # Wire edges
    # 1. Start with vector search → batch grade
    workflow.set_entry_point("vector_search")
    workflow.add_edge("vector_search", "batch_grade")

    # 2. After grading: relevant → live Reddit, irrelevant → rewrite query
    workflow.add_conditional_edges(
        "batch_grade",
        graph_edges.post_grade_decision,
        {
            "relevant": "live_reddit_search",
            "irrelevant": "transform_query",
        }
    )

    # 3. Rewritten query → web search → live Reddit
    workflow.add_edge("transform_query", "web_search")
    workflow.add_edge("web_search", "live_reddit_search")

    # 4. Live Reddit → generate
    workflow.add_edge("live_reddit_search", "generate")

    # 5. After generation: hallucination + quality check
    workflow.add_conditional_edges(
        "generate",
        graph_edges.post_generation_check,
        {
            "accept": "enrich_with_sources",
            "retry": "generate",
        }
    )

    # 6. Enrich → END
    workflow.add_edge("enrich_with_sources", END)

    return workflow.compile()


agent_workflow = compile_graph()
