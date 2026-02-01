# IBM watsonx Orchestrate Setup Guide

This guide matches the actual Orchestrate UI structure for configuring your Walking Route Planner agent.

## Prerequisites

1. IBM Cloud account with access to watsonx Orchestrate
2. Backend API running and accessible (via ngrok or deployed)

## Step 1: Create the Skill (Tool)

**Before creating the agent, you need to import your API as a Skill:**

1. In Orchestrate, go to **Build** → **Tools**
2. Click **Add tool** or **Import**
3. Select **Import from OpenAPI**
4. Upload the file: `openapi/openapi.yaml` (from your project)
5. Or enter URL: `https://your-ngrok-url.ngrok.io/openapi.json`
6. Review the imported operations and click **Import**
7. Name the skill: **"Walking Route Generator"**
8. **IMPORTANT**: Set the Server URL to your ngrok URL or deployed backend
9. Click **Save**

## Step 2: Create the AI Agent

Now create your agent with these exact settings:

### Profile Section

**Description:**
```
This agent helps users plan walking routes optimized for their preferences (vibes). It generates point-to-point routes or circular loops, avoiding or seeking specific features like parks, water, well-lit streets, or quiet areas. The agent maps natural language descriptions (e.g., "nature walk", "safe evening stroll") to technical routing parameters and explains why each route was chosen.
```

### Welcome Message

```
Hello, welcome to 歩く(Aruku) where we help you plan for your trips!
```

### Quick Start Prompts

Add these prompts (delete the existing text first):

**Prompt 1:**
```
I want a 30-minute nature walk with lots of greenery
```

**Prompt 2:**
```
Plan a safe evening stroll from my location
```

**Prompt 3:**
```
Find me a quiet, peaceful walking route away from crowds
```

### Agent Style

Select: **Default** (Recommended)

This relies on the model's intrinsic ability to understand, plan and call tools.

### Knowledge (Optional)

You can skip this for now, or add:
- Local walking safety tips
- Popular walking routes in your area

## Step 3: Add the Tool

**Critical Step - Add your skill to the agent:**

1. Scroll to **Toolset** section
2. Click **Add tool**
3. Select the **"Walking Route Generator"** skill you imported
4. Click **Add**

## Step 4: Configure Behavior

### Instructions (System Prompt)

Paste this into the **Instructions** field:

```
You are a helpful walking route planning assistant for 歩く(Aruku). Your job is to help users plan walking routes based on their mood and preferences (vibes).

## Your Capabilities
You can generate walking routes using the "Walking Route Generator" tool. This tool accepts:
- Origin coordinates (lat/lon) - THE FRONTEND WILL PROVIDE THIS when user clicks on map
- Destination coordinates (for point-to-point routes) - ask if needed for point-to-point
- Duration in minutes (for circular loops) - default to 30 if not specified
- Vibe preferences as floats from 0 to 1

## Location Handling
When the user has already selected a location on the map (the frontend sends this automatically), acknowledge it:
"I see you've selected a starting point on the map. Let me plan a route from there!"

Only ask for location if:
- The user hasn't clicked on the map yet
- The user wants to start from a different location than what's selected

## Vibe Mapping Guide
When users describe their ideal walk, map their words to these parameters:

- "nature walk", "green", "parks", "trees", "gardens" → greenery: 0.8-0.9
- "near water", "riverside", "beach", "lake", "waterfront" → blue_space: 0.7-0.9
- "quiet", "peaceful", "calm", "avoid crowds", "serene" → introvert_mode: 0.7-0.9
- "lively", "bustling", "shops", "cafes", "vibrant" → extrovert_mode: 0.7-0.9
- "safe", "secure", "well-lit", "evening walk", "night" → safety_check: 0.8-0.95
- "easy walking", "pedestrian paths", "sidewalks" → walkability: 0.8-0.9

## Conversation Flow
1. **Check for map selection**: If the frontend has sent location coordinates, acknowledge them
2. **Ask for destination** (only if point-to-point): "Where would you like to end your walk?"
3. **Confirm duration**: "How long would you like to walk for? (e.g., 30 minutes, 1 hour)"
4. **Clarify vibes**: "What's most important for this walk - being in nature, staying safe on well-lit streets, finding a quiet path, or exploring lively areas?"
5. **Call the tool** with mapped parameters including the coordinates from the frontend
6. **Explain the route**: After getting results, explain WHY this route was chosen based on the vibe scores achieved

## Response Format
When you receive route data, respond naturally like:
"I've planned a 2.3km route for you that will take about 35 minutes. This path was chosen because it passes through Ayala Triangle Gardens (excellent greenery!) and uses well-lit residential streets for safety."

## IMPORTANT RULES
- Check if location coordinates are already provided by the frontend (in the conversation context)
- Only ask for starting location if coordinates weren't provided
- For point-to-point routes, ask for the destination
- For circular loops, confirm duration (default: 30 min)
- Map natural language to vibe parameters before calling the tool
- Always include coordinates in the API call if available
- Explain the route choice after receiving results (transparency)
```

### Guidelines

Click **Add Guideline** and add these rules:

**Guideline 1:**
- **Rule**: Check if location coordinates are already provided by the frontend before asking
- **When to apply**: At the start of every route planning request

**Guideline 2:**
- **Rule**: For point-to-point routes, ask for the destination if not provided
- **When to apply**: When mode is "point_to_point" and destination is missing

**Guideline 3:**
- **Rule**: Convert natural language to vibe parameters using the mapping guide
- **When to apply**: Before calling the Walking Route Generator tool

**Guideline 4:**
- **Rule**: Always include coordinates in the API call if the frontend has provided them
- **When to apply**: When calling the route generation tool

**Guideline 5:**
- **Rule**: Explain why the route was chosen after receiving results
- **When to apply**: After successfully generating a route

## Step 5: Configure Channels

### Home Page
- ✅ **Show the agent on the Orchestrate Chat home page** - Enable this

### Embedded Agent (For Your Frontend)
1. Click **Embedded agent** > **Customize your chat UI**
2. Copy the embed code
3. Paste it into your `frontend/index.html` file, replacing the fallback chat section

The embed code will look like:
```html
<script>
  window.watsonAssistantChatOptions = {
    integrationID: "YOUR_INTEGRATION_ID",
    region: "YOUR_REGION",
    serviceInstanceID: "YOUR_SERVICE_INSTANCE_ID",
    onLoad: async (instance) => { await instance.render(); }
  };
</script>
<script src="https://web-chat.global.assistant.watson.appdomain.cloud/versions/latest/WatsonAssistantChatEntry.js"></script>
```

## Step 6: Save and Test

1. Click **Save** to save your agent
2. Click **Preview** to test the agent
3. Test with these prompts:
   - "I want a 30-minute nature walk"
   - "Plan a safe evening stroll starting from Makati"
   - "Find me a quiet route with lots of greenery"

## How the Frontend Provides Location

When the user clicks on the map in your frontend:

1. The map captures the lat/lon coordinates
2. The `orchestrate-bridge.js` sends these coordinates to the embedded Orchestrate chat via `postMessage`
3. The agent receives the location context automatically
4. The agent acknowledges: "I see you've selected a starting point on the map..."

This creates a seamless experience where the user doesn't have to type their location.

## Troubleshooting

### Skill not showing up in Tools
- Make sure you imported the OpenAPI spec first (Step 1)
- Verify the skill is published/active

### Agent not calling the backend
- Check the Server URL in the skill configuration
- Verify your backend is running and accessible
- Test the backend directly: `curl http://your-url/health`

### Location not being detected
- Check browser console for postMessage errors
- Ensure the embedded chat iframe is loaded before sending location
- Verify the orchestrate-bridge.js is properly initialized

### Model restrictions
Use ONLY these allowed models:
- `ibm/granite-13b-chat-v2` ✅
- `meta-llama/llama-3-2-90b-vision-instruct` ✅

Do NOT use:
- `meta-llama/llama-3-405b-instruct` ❌
- `mistral-medium` ❌

## Testing Checklist

- [ ] Skill imported successfully
- [ ] Skill added to agent's Toolset
- [ ] Server URL configured correctly
- [ ] Instructions (system prompt) pasted
- [ ] Guidelines added
- [ ] Welcome message set
- [ ] Quick start prompts added
- [ ] Home page channel enabled
- [ ] Agent responds correctly to test prompts
- [ ] Route data appears on map when embedded
- [ ] Frontend automatically sends location to agent
