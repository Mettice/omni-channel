---
description: Deploy Omni AI instance to a client
---

# Deploy Omni AI Workflow

Follow these steps to deploy a new instance of Omni AI for a client.

1. Ensure prerequisites (Supabase, Retell, n8n, OpenAI keys) are ready.
2. Clone this repository and create a new environment.
3. Configure the `.env` file based on `client-config-template.env`.
4. Run database migrations:
   - Apply `migrations/001_initial_schema.sql` to Supabase.
   - Apply `migrations/002_analytics_tables.sql` to Supabase.
5. Import workflows from `n8n-workflows/` to n8n.
6. Deploy backend to Railway.
   - Set all environment variables defined in `.env`.
   - Set start command to `python run.py`.
7. Deploy frontend to Vercel/Netlify.
   - Ensure `API_BASE` in `demo.html` is updated to the Railway URL.
8. Verify deployment by checking `https://[railway-app]/health`.
