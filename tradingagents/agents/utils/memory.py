import chromadb
from chromadb.config import Settings
from openai import OpenAI
import os
from dotenv import load_dotenv
import re

load_dotenv()

def clean_text(text):
    """清理文本中的特殊字符，避免编码问题"""
    if not isinstance(text, str):
        return str(text)
    # 移除零宽空格和其他特殊字符
    text = re.sub(r'[\u200b\u200c\u200d\u2060\u2061\u2062\u2063\u2064]', '', text)
    # 移除其他可能导致编码问题的字符
    text = text.encode('utf-8', errors='ignore').decode('utf-8')
    return text

# 暂时禁用 Deepseek embedding，因为 langchain_deepseek 包中没有 DeepSeekEmbeddings
HAS_DEEPSEEK = False

class FinancialSituationMemory:
    def __init__(self, name, config):
        self.llm_provider = config.get("llm_provider", "openai").lower()
        if self.llm_provider == "deepseek":
            # Deepseek 暂时不支持 embedding，使用 OpenAI embedding 作为备选
            print(clean_text("警告: Deepseek 暂不支持 embedding，使用 OpenAI embedding 作为备选"))
            self.embedding_client = OpenAI(base_url=config.get("backend_url", "https://api.openai.com/v1"), api_key=os.getenv("OPENAI_API_KEY"))
            self.embedding = "text-embedding-3-small"
        else:
            if config["backend_url"] == "http://localhost:11434/v1":
                self.embedding = "nomic-embed-text"
            else:
                self.embedding = "text-embedding-3-small"
            self.embedding_client = OpenAI(base_url=config["backend_url"], api_key=os.getenv("OPENAI_API_KEY"))
        self.chroma_client = chromadb.Client(Settings(allow_reset=True))
        self.situation_collection = self.chroma_client.create_collection(name=name)

    def get_embedding(self, text):
        """Get embedding for a text, auto switch provider"""
        if self.llm_provider == "deepseek":
            # 对于 Deepseek，使用 OpenAI embedding
            response = self.embedding_client.embeddings.create(
                model=self.embedding, input=text
            )
            return response.data[0].embedding
        else:
            # OpenAI embedding
            response = self.embedding_client.embeddings.create(
                model=self.embedding, input=text
            )
            return response.data[0].embedding

    def add_situations(self, situations_and_advice):
        """Add financial situations and their corresponding advice. Parameter is a list of tuples (situation, rec)"""

        situations = []
        advice = []
        ids = []
        embeddings = []

        offset = self.situation_collection.count()

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situations.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))
            embeddings.append(self.get_embedding(situation))

        self.situation_collection.add(
            documents=situations,
            metadatas=[{"recommendation": rec} for rec in advice],
            embeddings=embeddings,
            ids=ids,
        )

    def get_memories(self, current_situation, n_matches=1):
        """Find matching recommendations using embeddings"""
        query_embedding = self.get_embedding(current_situation)

        results = self.situation_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_matches,
            include=["metadatas", "documents", "distances"],
        )

        matched_results = []
        for i in range(len(results["documents"][0])):
            matched_results.append(
                {
                    "matched_situation": results["documents"][0][i],
                    "recommendation": results["metadatas"][0][i]["recommendation"],
                    "similarity_score": 1 - results["distances"][0][i],
                }
            )

        return matched_results


if __name__ == "__main__":
    # Example usage
    matcher = FinancialSituationMemory()

    # Example data
    example_data = [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities. Review fixed-income portfolio duration.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling pressure",
            "Reduce exposure to high-growth tech stocks. Look for value opportunities in established tech companies with strong cash flows.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions. Consider reducing allocation to emerging market debt.",
        ),
        (
            "Market showing signs of sector rotation with rising yields",
            "Rebalance portfolio to maintain target allocations. Consider increasing exposure to sectors benefiting from higher rates.",
        ),
    ]

    # Add the example situations and recommendations
    matcher.add_situations(example_data)

    # Example query
    current_situation = """
    Market showing increased volatility in tech sector, with institutional investors 
    reducing positions and rising interest rates affecting growth stock valuations
    """

    try:
        recommendations = matcher.get_memories(current_situation, n_matches=2)

        for i, rec in enumerate(recommendations, 1):
            print(f"\nMatch {i}:")
            print(f"Similarity Score: {rec['similarity_score']:.2f}")
            print(f"Matched Situation: {rec['matched_situation']}")
            print(f"Recommendation: {rec['recommendation']}")

    except Exception as e:
        print(f"Error during recommendation: {str(e)}")
