# Dialogflow CX Agent: Intent Manager

A robust and modular solution for managing Dialogflow CX agent configurations, including the ability to enrich training phrases using the Gemini API. Define entities and intents declaratively in YAML, and deploy them to your Dialogflow CX agent.

---

## ✨ Features

- **Declarative Configuration:** Define Dialogflow CX entities and intents in a human-readable YAML file (`agent_config_params.yaml`).
- **Gemini AI-Powered Training Phrase Enrichment:** Optionally enhance your intent's training phrases by leveraging the Gemini API to generate new, diverse, and natural language examples.
- **Dynamic Entity Recognition:** Automatically format generated training phrases to include existing Dialogflow CX entities.
---

## 📁 Project Structure

```
.
├── config.yaml                     # Centralized project configuration
├── gemini_enricher.py              # Gemini-powered training phrase generation
├── dialogflow_agent_manager.py     # Dialogflow CX agent resource creation (entities, intents)
├── main.py                         # Main script to orchestrate the workflow
├── agent_config_params.yaml        # Original Dialogflow CX agent configuration (entities and intents)
├── enriched_agent_config.yaml      # (Generated) Enriched configuration with Gemini-generated training phrases
└── requirements.txt                # Python dependencies
```

---

## 🛠️ Installation

1. **Clone the Repository:**
   ```sh
   git clone <your-repository-url>
   cd <your-project-directory>
   ```

2. **Create a Virtual Environment (Recommended):**
   ```sh
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Google Cloud Service Account Key:**
   - Ensure you have a Google Cloud service account key file with the necessary Dialogflow CX permissions.
   - This file's path will be used in `config.yaml`.
   - Permissions typically include: **Dialogflow CX API Editor** or equivalent.

---

## ⚙️ Configuration

All configurable aspects of the project are managed in the `config.yaml` file. Open this file and update the parameters as per your environment and requirements.

### Example `config.yaml`:

```yaml
dialogflow:
  creds_path: "/path/to/your/gcp/service-account-key.json" # REQUIRED: Path to your GCP service account key file
  agent_path: "projects/<PROJECT_ID>/locations/<LOCATION_ID>/agents/<AGENT_ID>" # REQUIRED: Your Dialogflow CX agent path

agent_config:
  original_file: "agent_config_params.yaml" # Default: Original agent configuration file
  enriched_file: "enriched_agent_config.yaml" # Default: Output file for Gemini-enriched configuration

gemini_enrichment:
  enabled: true # Set to true to enable Gemini training phrase generation, false to skip
  api_key: "YOUR_GEMINI_API_KEY_HERE" # REQUIRED if enabled: Your Gemini API Key
  phrases_to_generate: 5 # Number of new training phrases to generate per intent
```

### Configuration Options Explained

- **dialogflow.creds_path**:  
  *Type:* String  
  *Description:* Path to your Google Cloud service account JSON key file.  
  *Example:* `/Users/youruser/keys/my-dfcx-key.json`

- **dialogflow.agent_path**:  
  *Type:* String  
  *Description:* Full resource path to your Dialogflow CX agent.  
  *Example:* `projects/my-google-cloud-project/locations/us-central1/agents/a1b2c3d4-e5f6-7890-abcd-ef1234567890`

- **agent_config.original_file**:  
  *Type:* String  
  *Description:* Filename of your base agent configuration YAML file.

- **agent_config.enriched_file**:  
  *Type:* String  
  *Description:* Filename for the output YAML file with Gemini-generated training phrases.

- **gemini_enrichment.enabled**:  
  *Type:* Boolean  
  *Description:* Set to `true` to activate Gemini API for generating additional training phrases.

- **gemini_enrichment.api_key**:  
  *Type:* String  
  *Description:* Your Google Gemini API key.  
  *Note:* Never commit your API keys directly into public repositories. Use environment variables for production.

- **gemini_enrichment.phrases_to_generate**:  
  *Type:* Integer  
  *Description:* Number of new training phrases Gemini will attempt to generate for each intent.

---

## 🚀 Usage

Once configured, run the main script:

```sh
python main.py
```

The script will:

1. **Load Configuration:** Reads settings from `config.yaml`.
2. **Gemini Enrichment (Conditional):**
   - If `gemini_enrichment.enabled` is `true`:
     - Loads `agent_config_params.yaml`.
     - Uses the Gemini API to generate `phrases_to_generate` new training phrases for each intent.
     - Formats new phrases to include existing entities.
     - Saves the enriched configuration to `enriched_agent_config.yaml`.
   - If `gemini_enrichment.enabled` is `false`:
     - Proceeds directly with `agent_config_params.yaml`.
3. **Dialogflow CX Agent Management:**
   - Initializes Dialogflow CX clients using your credentials and agent path.
   - **Creates/Updates Entities:** Deploys custom entities defined in the chosen configuration file to your Dialogflow CX agent (skips existing).
   - **Creates/Updates Intents:** Deploys intents defined in the chosen configuration file (skips existing).
   - **Lists Current Intents:** After processing, lists all intents present in your agent for verification.

Monitor the console output for progress messages and any potential errors.

---


## 📄 License

This project is open-sourced under the MIT License. See the [LICENSE](LICENSE) file for more details.
