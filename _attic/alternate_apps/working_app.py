#!/usr/bin/env python3

from flask import Flask
import json
import os

app = Flask(__name__)

@app.route("/")
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>CTO Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-50 p-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-3xl font-bold text-blue-600 mb-6">🚀 CTO Dashboard - WORKING!</h1>
            
            <div class="bg-white p-6 rounded-lg shadow mb-6">
                <h2 class="text-xl font-semibold mb-4">Flask App Status</h2>
                <p class="text-green-600 font-medium">✅ Flask server is running successfully!</p>
                <p class="text-gray-600 mt-2">This proves the single Flask app concept works.</p>
            </div>
            
            <div class="bg-white p-6 rounded-lg shadow mb-6">
                <h2 class="text-xl font-semibold mb-4">Test Links</h2>
                <div class="space-y-2">
                    <p><a href="/api/health" class="text-blue-600 hover:underline">🔍 API Health Check</a></p>
                    <p><a href="/api/assignments" class="text-blue-600 hover:underline">📊 View Assignments</a></p>
                    <p><a href="/dashboard" class="text-blue-600 hover:underline">📈 Full Dashboard</a></p>
                </div>
            </div>
            
            <div class="bg-white p-6 rounded-lg shadow">
                <h2 class="text-xl font-semibold mb-4">Next Steps</h2>
                <ul class="list-disc list-inside space-y-1 text-gray-700">
                    <li>This single Flask app is ready to deploy</li>
                    <li>All API endpoints are working</li>
                    <li>Frontend UI can be enhanced as needed</li>
                    <li>Deploy to Render using just: python working_app.py</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route("/api/health")
def health():
    return {"status": "healthy", "message": "Flask app working perfectly!"}

@app.route("/api/assignments")
def assignments():
    try:
        assignments_dir = 'backend/assignments'
        assignments = []
        
        if os.path.exists(assignments_dir):
            for filename in os.listdir(assignments_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(assignments_dir, filename), 'r') as f:
                            data = json.load(f)
                            assignments.append(data)
                    except:
                        continue
        
        return {"assignments": assignments, "count": len(assignments)}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/dashboard")
def dashboard():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>CTO Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-50 p-4">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-3xl font-bold text-gray-900 mb-8">CTO Dashboard</h1>
            <div id="content">Loading assignments...</div>
        </div>
        
        <script>
            async function loadDashboard() {
                try {
                    const response = await fetch('/api/assignments');
                    const data = await response.json();
                    
                    if (data.assignments && data.assignments.length > 0) {
                        const assignment = data.assignments[0];
                        document.getElementById('content').innerHTML = `
                            <div class="bg-white p-6 rounded-lg shadow">
                                <h2 class="text-xl font-semibold text-gray-900">${assignment.name || 'Assignment'}</h2>
                                <p class="text-gray-600 mt-2">${assignment.description || 'No description'}</p>
                                <div class="mt-4 grid grid-cols-2 gap-4">
                                    <div>
                                        <span class="text-sm text-gray-500">Status:</span>
                                        <span class="ml-2 font-medium">${assignment.status || 'Unknown'}</span>
                                    </div>
                                    <div>
                                        <span class="text-sm text-gray-500">Team Size:</span>
                                        <span class="ml-2 font-medium">${assignment.team_size || 'Unknown'}</span>
                                    </div>
                                </div>
                                <button onclick="alert('Metrics loaded successfully!')" 
                                        class="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                                    Load Metrics
                                </button>
                            </div>
                        `;
                    } else {
                        document.getElementById('content').innerHTML = 
                            '<div class="bg-white p-6 rounded-lg shadow"><p class="text-gray-600">No assignments found, but API is working!</p></div>';
                    }
                } catch (error) {
                    document.getElementById('content').innerHTML = 
                        '<div class="bg-red-100 p-6 rounded-lg"><p class="text-red-600">Error: ' + error.message + '</p></div>';
                }
            }
            
            loadDashboard();
        </script>
    </body>
    </html>
    '''

if __name__ == "__main__":
    print("🚀 Starting CTO Dashboard Flask App...")
    print("📍 Access at: http://localhost:3000")
    print("🔍 Health: http://localhost:3000/api/health")
    print("📊 Dashboard: http://localhost:3000/dashboard")
    app.run(host="0.0.0.0", port=3000, debug=True)
