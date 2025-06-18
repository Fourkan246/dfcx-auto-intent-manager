import yaml
import logging
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.entity_types import EntityTypes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DialogflowAgentManager:
    def __init__(self, creds_path: str, agent_path: str):
        """
        Initializes the DialogflowAgentManager with credentials and agent path.
        
        Args:
            creds_path (str): Path to your GCP service account key file.
            agent_path (str): Your Dialogflow CX agent path (e.g., 'projects/projectId/locations/locationId/agents/agentId').
        """
        try:
            self.intents_client = Intents(creds_path=creds_path, agent_id=agent_path)
            self.entities_client = EntityTypes(creds_path=creds_path, agent_id=agent_path)
            self.agent_path = agent_path
            logging.info(f"✅ Successfully initialized clients for agent: {agent_path}")
        except Exception as e:
            logging.error(f"❌ Error initializing Dialogflow CX clients: {e}")
            raise

    def create_entities(self, config_data: dict):
        """
        Creates custom entities in Dialogflow CX based on the provided configuration.
        
        Args:
            config_data (dict): The loaded YAML configuration data.
        """
        if "entities" in config_data:
            for entity in config_data["entities"]:
                display_name = entity.get("display_name")
                entries = entity.get("entries", [])
                kind = entity.get("kind", "KIND_MAP")
                auto_expansion = entity.get("auto_expansion_mode", "AUTO_EXPANSION_MODE_DEFAULT")

                if not display_name:
                    logging.warning(f"Skipping entity due to missing display_name: {entity}")
                    continue

                formatted_entries = [{"value": e["value"], "synonyms": e.get("synonyms", [])} for e in entries]

                try:
                    self.entities_client.create_entity_type(
                        display_name=display_name,
                        kind=kind,
                        auto_expansion_mode=auto_expansion,
                        entities=formatted_entries
                    )
                    logging.info(f"✅ Created custom entity: {display_name}")
                except Exception as e:
                    if "ALREADY_EXISTS" in str(e).upper():
                        logging.info(f"⚠️ Entity '{display_name}' already exists. Skipping.")
                    else:
                        logging.error(f"❌ Error creating entity '{display_name}': {e}")
        else:
            logging.info("ℹ️ No custom entities defined in YAML.")

    def create_intents(self, config_data: dict):
        """
        Creates intents in Dialogflow CX based on the provided configuration.
        
        Args:
            config_data (dict): The loaded YAML configuration data.
        """
        intents_to_create = config_data.get("intents", [])
        for intent_data in intents_to_create:
            display_name = intent_data.get('display_name')
            raw_training_phrases = intent_data.get('training_phrases', [])

            if not display_name:
                logging.warning(f"Skipping intent due to missing display_name: {intent_data}")
                continue

            logging.info(f"\n🚀 Processing intent: '{display_name}'")

            # Format training phrases
            formatted_training_phrases = []
            for phrase_item in raw_training_phrases:
                if isinstance(phrase_item, str):
                    formatted_training_phrases.append({
                        "parts": [{"text": phrase_item}],
                        "repeat_count": 1
                    })
                elif isinstance(phrase_item, dict) and "text_parts" in phrase_item:
                    parts = phrase_item["text_parts"]
                    if all("text" in part for part in parts):
                        formatted_training_phrases.append({
                            "parts": parts,
                            "repeat_count": phrase_item.get("repeat_count", 1)
                        })
                    else:
                        logging.warning(f"Skipping malformed 'text_parts': {phrase_item} for intent '{display_name}'")
                else:
                    logging.warning(f"Unrecognized training phrase format: {phrase_item} for intent '{display_name}'")

            # Format parameters
            formatted_intent_parameters = []
            for param in intent_data.get('parameters', []):
                param_id = param.get('id')
                entity_type = param.get('entity_type_display_name')

                if not (param_id and entity_type):
                    logging.warning(f"Skipping malformed parameter for '{display_name}': {param}")
                    continue

                # Resolve custom entity to full resource path
                entity_type_api = self._resolve_entity_type_path(entity_type)
                if not entity_type_api:
                    logging.error(f"❌ Could not resolve entity type '{entity_type}' for intent '{display_name}'. Skipping parameter.")
                    continue

                param_dict = {
                    "id": param_id,
                    "entity_type": entity_type_api,
                    "is_list": param.get("is_list", False)
                }
                formatted_intent_parameters.append(param_dict)

            # Final payload for intent creation
            try:
                payload = {
                    "agent_id": self.intents_client.agent_id,
                    "display_name": display_name,
                    "training_phrases": formatted_training_phrases,
                    "description": intent_data.get('description', f"Intent for {display_name}"),
                    "priority": intent_data.get('priority', 500000),
                    "is_fallback": intent_data.get('is_fallback', False)
                }
                if formatted_intent_parameters:
                    payload["parameters"] = formatted_intent_parameters

                created_intent = self.intents_client.create_intent(**payload)
                logging.info(f"✅ Created intent: '{created_intent.display_name}'")

            except Exception as e:
                if "already exists" in str(e).lower():
                    logging.info(f"⚠️ Intent '{display_name}' already exists. Skipping.")
                else:
                    logging.error(f"❌ Error creating intent '{display_name}': {e}")
        
        self.list_current_intents()

    def _resolve_entity_type_path(self, entity_type_display_name: str) -> str:
        """
        Resolves a custom entity display name to its full resource path.
        
        Args:
            entity_type_display_name (str): The display name of the entity type.
            
        Returns:
            str: The full resource path of the entity type, or None if not found.
        """
        if entity_type_display_name.startswith('@sys.'):
            return f"projects/-/locations/-/agents/-/entityTypes/{entity_type_display_name[1:]}"
        else:
            try:
                all_entities = self.entities_client.list_entity_types(agent_id=self.agent_path)
                for ent in all_entities:
                    if ent.display_name == entity_type_display_name:
                        return ent.name
                return None
            except Exception as e:
                logging.error(f"Error resolving custom entity '{entity_type_display_name}': {e}")
                return None

    def list_current_intents(self):
        """Lists all current intents in the Dialogflow CX agent."""
        logging.info("\n📋 Listing current intents:")
        try:
            df = self.intents_client.bulk_intent_to_df()
            for name in sorted(df['display_name'].unique()):
                logging.info(f"- {name}")
        except Exception as e:
            logging.error(f"❌ Error fetching intents: {e}")

