import yaml
import google.generativeai as genai
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GeminiEnricher:
    def __init__(self, api_key: str, phrases_to_generate: int):
        """
        Initializes the GeminiEnricher with the Gemini API key and desired number of phrases.
        
        Args:
            api_key (str): Your Gemini API key.
            phrases_to_generate (int): The number of new training phrases to generate per intent.
        """
        if not api_key:
            raise ValueError("Gemini API key cannot be empty.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        self.phrases_to_generate = phrases_to_generate
        logging.info("GeminiEnricher initialized.")

    def _prepare_entities_for_matching(self, config_data: dict) -> list:
        """
        Extracts and flattens all entities and their synonyms for easy lookup.
        Sorts by length descending to prioritize longer matches.
        
        Args:
            config_data (dict): The loaded YAML configuration data.
            
        Returns:
            list: A list of dictionaries, each with 'text' and 'parameter_id'.
        """
        all_entities_for_matching = []
        for entity_obj in config_data.get("entities", []):
            entity_name = entity_obj["display_name"]
            for entry in entity_obj.get("entries", []):
                values_to_check = [entry["value"]] + entry.get("synonyms", [])
                for val in values_to_check:
                    all_entities_for_matching.append({
                        "text": val,
                        "parameter_id": entity_name
                    })
        # Sort by the length of the 'text' key in descending order for greedy matching.
        all_entities_for_matching.sort(key=lambda x: len(x["text"]), reverse=True)
        logging.info(f"Prepared {len(all_entities_for_matching)} entities for matching.")
        return all_entities_for_matching

    def _format_phrase_with_entities(self, phrase: str, entities_for_matching: list) -> dict or str:
        """
        Formats a plain text phrase into Dialogflow CX 'text_parts' format,
        identifying and tagging entities based on the provided entity list.
        
        Args:
            phrase (str): The plain text phrase.
            entities_for_matching (list): List of entities prepared for matching.
            
        Returns:
            dict or str: Formatted phrase as a dictionary with 'text_parts' or a simple string.
        """
        parts = []
        current_index = 0
        
        while current_index < len(phrase):
            best_match = None
            best_match_text = ""
            best_match_param_id = None
            best_match_start = -1

            # Search for the longest entity match starting from the current_index
            for em in entities_for_matching:
                entity_text = em["text"]
                param_id = em["parameter_id"]
                
                # Use re.IGNORECASE for case-insensitive matching
                match = re.search(re.escape(entity_text), phrase[current_index:], re.IGNORECASE)
                
                if match and match.start() == 0: # If the entity is found at the beginning of the remaining string
                    if len(entity_text) > len(best_match_text): # Prioritize longest match
                        best_match = match
                        best_match_text = entity_text
                        best_match_param_id = param_id
                        best_match_start = current_index
            
            if best_match:
                # Add the text before the entity if any
                if best_match_start > 0: # Check if there's plain text before the entity at current_index
                    parts.append({"text": phrase[current_index:current_index + best_match.start()]})
                
                # Add the entity part
                matched_text_in_phrase = phrase[current_index + best_match.start() : current_index + best_match.end()]
                parts.append({"text": matched_text_in_phrase, "parameter_id": best_match_param_id})
                
                current_index += best_match.end()
            else:
                # If no entity is found at current_index, add the next segment of plain text
                next_entity_start_index = len(phrase)
                for em in entities_for_matching:
                    # Find the first occurrence of any entity *after* current_index
                    match = re.search(re.escape(em["text"]), phrase[current_index:], re.IGNORECASE)
                    if match:
                        next_entity_start_index = min(next_entity_start_index, current_index + match.start())
                
                # Add the plain text segment up to the next found entity or end of string
                if next_entity_start_index > current_index:
                    parts.append({"text": phrase[current_index:next_entity_start_index]})
                    current_index = next_entity_start_index
                else:
                    # Fallback: if no further entities are found, add the rest of the phrase as plain text
                    parts.append({"text": phrase[current_index:]})
                    current_index = len(phrase) # Move current_index to the end to terminate loop
                    
        # If the phrase consists of a single part that is not an entity, return it as a simple string
        if len(parts) == 1 and "parameter_id" not in parts[0]:
            return parts[0]["text"]
        else:
            # Otherwise, return it in the text_parts format
            return {"text_parts": parts}

    def _generate_training_phrases_with_gemini(self, intent_name: str, description: str, existing_phrases: list) -> list:
        """
        Generates new training phrases using Gemini, ensuring clean output without
        introductory remarks or numbering.
        
        Args:
            intent_name (str): The display name of the intent.
            description (str): The description of the intent.
            existing_phrases (list): A list of existing training phrases for context.
            
        Returns:
            list: A list of newly generated plain text phrases.
        """
        prompt = f"""You are a Dialogflow CX assistant. Your task is to generate new, diverse, and natural training phrases for a given intent. Do not include any introductory or concluding remarks, just the phrases themselves, one per line. Do not number the phrases.

Here is the intent information:
Intent name: "{intent_name}"
Description: "{description}"
Existing training phrases (for context, do not regenerate these):
{chr(10).join(f"- {phrase}" for phrase in existing_phrases)}

Generate {self.phrases_to_generate} new diverse and natural training phrases that match the above intent. Each phrase should be on a new line.
"""
        
        try:
            response = self.model.generate_content(prompt)
            # Post-process the response to remove any numbering, leading dashes, or extra whitespace
            generated_phrases = []
            for line in response.text.strip().split("\n"):
                # Use regex to remove common prefixes like numbers (e.g., "1. ", "2. ")
                # and potential leading dashes or asterisks (e.g., "- ", "* ")
                cleaned_line = re.sub(r"^\s*(\d+\.?\s*|[-*]\s*)?", "", line).strip()
                if cleaned_line: # Only add non-empty lines
                    generated_phrases.append(cleaned_line)
            logging.info(f"Generated {len(generated_phrases)} phrases for '{intent_name}'.")
            return generated_phrases
        except Exception as e:
            logging.error(f"Error generating phrases for '{intent_name}': {e}")
            return []

    def enrich_agent_config(self, config_data: dict) -> dict:
        """
        Enriches the agent configuration with Gemini-generated training phrases.
        
        Args:
            config_data (dict): The loaded YAML configuration data.
            
        Returns:
            dict: The updated configuration data with enriched training phrases.
        """
        enriched_data = config_data.copy()
        
        # Prepare entities for matching *before* iterating through intents
        all_entities_for_matching = self._prepare_entities_for_matching(enriched_data)

        for intent in enriched_data.get("intents", []):
            name = intent["display_name"]
            desc = intent.get("description", "")
            existing_phrases = []

            # Collect existing training phrases, flattening text_parts into simple strings if necessary,
            # so they can be passed to Gemini for context.
            if "training_phrases" in intent:
                for tp in intent["training_phrases"]:
                    if isinstance(tp, str):
                        existing_phrases.append(tp)
                    elif isinstance(tp, dict) and "text_parts" in tp:
                        text = "".join(part["text"] for part in tp["text_parts"])
                        existing_phrases.append(text)

                # Generate new plain text phrases using Gemini
                new_plain_phrases = self._generate_training_phrases_with_gemini(name, desc, existing_phrases)
                
                # Format the newly generated phrases with entity detection
                new_formatted_phrases = []
                for phrase in new_plain_phrases:
                    formatted_phrase = self._format_phrase_with_entities(phrase, all_entities_for_matching)
                    new_formatted_phrases.append(formatted_phrase)

                logging.info(f"Generated and formatted for '{name}': {new_formatted_phrases}")

                # Append the new formatted phrases to the intent's training_phrases list
                if "training_phrases" in intent:
                    intent["training_phrases"].extend(new_formatted_phrases)
                else:
                    intent["training_phrases"] = new_formatted_phrases
            else:
                logging.warning(f"Intent '{name}' has no 'training_phrases' key. Skipping enrichment for this intent.")

        logging.info("Agent configuration enrichment complete.")
        return enriched_data

