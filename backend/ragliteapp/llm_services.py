import requests
import logging
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.urls = settings.LLM_URLS
    
    def generate_answer(
        self,
        query:str,
        context:str,
        temperature:float =0.7,
        model_name:str = "llama3.2",
    ) -> Optional[str]:
        """
        Generate an answer using Ollama LLM
        
        Args:
            question: The user's question
            context: Retrieved context from documents
            temperature: LLM temperature (0.0 = deterministic, 1.0 = creative)
            model_name: LLM model name
            
        Returns:
            Generated answer or None if error
        """
    
        # build prompt
        prompt = self._build_prompt(query, context)
        try:
            # fetching url based on model_name received from user input
            target_url = None
            for url_entry in self.urls:
                if url_entry['model'] == model_name:
                    target_url = url_entry['url']
                    break
            
            if target_url is None:
                logger.error(f"Model {model_name} not found")
                return "Model not found"
        
            # make request to ollama
            response = requests.post(
                target_url,
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature
                    }
                },
                # timeout is set to 1 hour
                timeout=3600
            )
            response.raise_for_status()
            result = response.json()
            answer = result.get("response", "")
            logger.info(f"Generated answer: {answer}")
            return answer
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            return "OLF"
        except requests.exceptions.Timeout as e:
            logger.error(f"Ollama request timed out: {e}")
            return "OLT"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return "OLU"
    
    def _build_prompt(self, query:str, context:str) -> str:
        """
        Build the prompt for the LLM
        
        Args:
            question: User's question
            context: Retrieved document context
            
        Returns:
            Formatted prompt
        """
        prompt = f""" You are a helpful assistant that answers questions based on provided context.
        Context from documents: {context}
        Question: {query}
        Instructions: 
        - Answer the question based ONLY on the provided context
        - If the answer is not in the context, say "I don't have enough information to answer that question."
        - Be concise and accurate
        - Cite specific details from the context when possible
        Answer:"""
        return prompt
        
    def health_check(self) -> bool:
        """
        Check if the LLM service is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = requests.get("http://localhost:11434/health")
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False
# Singleton instance of LLMService
_llm_service = None

def get_llm_service() -> LLMService:
    """ get or create llm service instance """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service