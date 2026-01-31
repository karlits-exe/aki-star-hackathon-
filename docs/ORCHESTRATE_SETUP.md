# IBM watsonx Orchestrate Setup Guide

This guide explains how to configure IBM watsonx Orchestrate to work with the Walking Route Planner backend.

## Prerequisites

1. IBM Cloud account with access to watsonx Orchestrate
2. Backend API running and accessible (via ngrok or deployed)

## Step 1: Access watsonx Orchestrate

1. Log in to [IBM Cloud](https://cloud.ibm.com)
2. Navigate to **watsonx Orchestrate** from the catalog or your resource list
3. Launch the Orchestrate workspace

## Step 2: Import the OpenAPI Spec as a Custom Skill

### Option A: Import from URL (if backend is deployed)

1. In Orchestrate, go to **Skills** > **Add skills**
2. Select **Import from OpenAPI**
3. Enter the URL: `https://your-ngrok-url.ngrok.io/openapi.json`
4. Click **Import**

### Option B: Upload OpenAPI File

1. Go to **Skills** > **Add skills** > **Import from OpenAPI**
2. Upload the file: `openapi/openapi.yaml`
3. Review the imported operations
4. Click **Import**

## Step 3: Configure the Skill

After importing, configure the skill:

1. **Skill Name**: "Walking Route Generator"
2. **Description**: "Generate walking routes based on vibes like greenery, safety, and quietness"
3. **Server URL**: Update to your ngrok URL or deployed backend URL

## Step 4: Create an AI Assistant

1. Go to **AI assistants** > **Create assistant**
2. Name it: "Walk Planner Assistant"
3. Add the imported skill to the assistant

## Step 5: Configure the System Prompt

In the assistant settings, set the following system prompt:

```
You are a helpful walking route planning assistant. Your job is to help users plan walking routes based on their mood and preferences (vibes).

## Your Capabilities
You can generate walking routes using the "generateWalkingRoute" skill. This skill accepts:
- Origin coordinates (lat/lon)
- Destination coordinates (for point-to-point routes)
- Duration in minutes (for circular loops)
- Vibe preferences as floats from 0 to 1

## Vibe Mapping
When users describe their ideal walk, map their words to vibe parameters:

| User Says | Parameter | Value |
|-----------|-----------|-------|
| "nature walk", "green", "parks" | greenery | 0.8-0.9 |
| "near water", "riverside", "beach" | blue_space | 0.7-0.9 |
| "quiet", "peaceful", "calm", "avoid crowds" | introvert_mode | 0.7-0.9 |
| "lively", "bustling", "shops", "cafes" | extrovert_mode | 0.7-0.9 |
| "safe", "well-lit", "evening walk" | safety_check | 0.8-0.95 |
| "easy walking", "pedestrian paths" | walkability | 0.8-0.9 |

## Conversation Flow

1. **Greet and Ask**: If the user hasn't specified a location, ask where they want to start
2. **Clarify Vibes**: If the user's preferences are unclear, ask what kind of experience they want
3. **Confirm Duration**: For loop walks, confirm how long they want to walk
4. **Generate Route**: Call the skill with appropriate parameters
5. **Explain Route**: After getting results, explain WHY this route was chosen (transparency)

## IMPORTANT: Model Restrictions
- You MUST use allowed models: `ibm/granite-13b-chat-v2` or `meta-llama/llama-3-2-90b-vision-instruct`
- Do NOT use: `llama-3-405b-instruct`, `mistral-medium`, or other restricted models

## Example Interactions

User: "I want a nature walk"
Assistant: "I'd love to help you plan a nature walk! Where would you like to start? And how long would you like to walk - maybe 30 minutes or an hour?"

User: "Start from BGC, about 45 minutes"
Assistant: "Perfect! A 45-minute nature walk starting from BGC. Let me find a route that maximizes green spaces and parks..."
[Calls skill with greenery=0.9, duration_minutes=45]

User: "Plan a safe evening stroll"
Assistant: "For a safe evening walk, I'll prioritize well-lit streets. Where are you starting from?"
```

## Step 6: Test the Assistant

1. Open the assistant chat interface
2. Try these test prompts:
   - "I want a 30-minute nature walk"
   - "Plan a safe evening stroll starting from [location]"
   - "Find me a quiet, peaceful walking route"

## Step 7: Embed in Frontend

To embed the assistant in your frontend:

1. Go to **Integrations** > **Web chat**
2. Copy the embed script
3. Paste into `frontend/index.html` in the chat container section

The embed code looks like:
```html
<script src="https://web-chat.global.assistant.watson.appdomain.cloud/versions/latest/WatsonAssistantChatEntry.js"></script>
<script>
  window.watsonAssistantChatOptions = {
    integrationID: "YOUR_INTEGRATION_ID",
    region: "YOUR_REGION", 
    serviceInstanceID: "YOUR_SERVICE_INSTANCE_ID",
    onLoad: async (instance) => { await instance.render(); }
  };
</script>
```

## Troubleshooting

### Skill not calling backend
- Verify the server URL is correct and accessible
- Check CORS settings on the backend
- Test the backend directly with curl/Postman

### Route not rendering on map
- Ensure the frontend is listening for route data in chat responses
- Check browser console for JavaScript errors
- Verify GeoJSON format is correct

### Model errors
- Ensure you're using allowed models (Granite or Llama 3.2)
- Check your watsonx.ai project has the model enabled

## Allowed Models Reference

Per hackathon rules, use ONLY these models:
- `ibm/granite-13b-chat-v2` (Recommended)
- `ibm/granite-20b-multilingual`
- `meta-llama/llama-3-2-90b-vision-instruct`
- `meta-llama/llama-3-2-11b-vision-instruct`

Do NOT use:
- `meta-llama/llama-3-405b-instruct`
- `mistral-medium`
- Any other restricted models
