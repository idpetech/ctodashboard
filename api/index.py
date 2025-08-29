from integrated_dashboard import app

# Vercel serverless function entry point
def handler(request):
    return app(request.environ, lambda x, y: None)
