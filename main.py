import yaml
import logging
from gemini_enricher import GeminiEnricher
from dialogflow_agent_manager import DialogflowAgentManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(config_path: str) -> dict:
    """
    Loads the YAML configuration file.
    
    Args:
        config_path (str): The path to the configuration file.
        
    Returns:
        dict: The loaded configuration.
    """
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        if not config:
            raise ValueError(f"Configuration file '{config_path}' is empty.")
        logging.info(f"Configuration loaded from '{config_path}' successfully.")
        return config
    except FileNotFoundError:
        logging.error(f"Error: Configuration file '{config_path}' not found.")
        exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing configuration file '{config_path}': {e}")
        exit(1)
    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        exit(1)

def main():
    config = load_config("config.yaml")

    # Determine which agent config file to use
    use_gemini_enrichment = config['gemini_enrichment']['enabled']
    
    if use_gemini_enrichment:
        agent_config_file_path = config['agent_config']['enriched_file']
        original_config_file_path = config['agent_config']['original_file']

        logging.info(f"Gemini enrichment is ENABLED. Loading original config from '{original_config_file_path}' for enrichment.")
        try:
            with open(original_config_file_path, 'r') as f:
                agent_config_data = yaml.safe_load(f)
        except FileNotFoundError:
            logging.error(f"Error: Original agent configuration file '{original_config_file_path}' not found.")
            exit(1)
        except yaml.YAMLError as e:
            logging.error(f"Error parsing original agent configuration file '{original_config_file_path}': {e}")
            exit(1)

        # Initialize and run Gemini Enricher
        gemini_api_key = config['gemini_enrichment']['api_key']
        phrases_to_generate = config['gemini_enrichment']['phrases_to_generate']
        
        try:
            enricher = GeminiEnricher(api_key=gemini_api_key, phrases_to_generate=phrases_to_generate)
            enriched_agent_config_data = enricher.enrich_agent_config(agent_config_data)

            # Save the enriched configuration to a new file
            with open(agent_config_file_path, "w", encoding="utf-8") as f:
                yaml.dump(enriched_agent_config_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True, indent=2)
            logging.info(f"Enriched configuration saved to '{agent_config_file_path}'")

        except ValueError as e:
            logging.error(f"Gemini enrichment setup error: {e}")
            exit(1)
        except Exception as e:
            logging.error(f"An unexpected error occurred during Gemini enrichment: {e}")
            exit(1)
            
    else:
        agent_config_file_path = config['agent_config']['original_file']
        logging.info(f"Gemini enrichment is DISABLED. Using original config from '{agent_config_file_path}'.")
        try:
            with open(agent_config_file_path, 'r') as f:
                agent_config_data = yaml.safe_load(f)
        except FileNotFoundError:
            logging.error(f"Error: Original agent configuration file '{agent_config_file_path}' not found.")
            exit(1)
        except yaml.YAMLError as e:
            logging.error(f"Error parsing original agent configuration file '{agent_config_file_path}': {e}")
            exit(1)

    # Initialize and run Dialogflow Agent Manager
    creds_path = config['dialogflow']['creds_path']
    agent_path = config['dialogflow']['agent_path']

    try:
        agent_manager = DialogflowAgentManager(creds_path=creds_path, agent_path=agent_path)
        
        # Create entities first as intents might depend on them
        agent_manager.create_entities(agent_config_data)
        agent_manager.create_intents(agent_config_data)
        
    except Exception as e:
        logging.error(f"An error occurred during Dialogflow agent management: {e}")
        exit(1)

if __name__ == "__main__":
    main()

