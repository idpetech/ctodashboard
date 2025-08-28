#!/bin/bash
# Simple integration test script

echo "🧪 Running Full Stack Integration Test"

# Test 1: Backend API
echo "1️⃣ Testing Backend API..."
cd backend
source .venv/bin/activate
python main.py &
BACKEND_PID=$!
sleep 2

# Test API endpoints
echo "   Testing /health endpoint..."
curl -s http://localhost:8000/health | grep "healthy" && echo "   ✅ Health check passed" || echo "   ❌ Health check failed"

echo "   Testing /assignments endpoint..."
curl -s http://localhost:8000/assignments | grep "ideptech" && echo "   ✅ Assignments API passed" || echo "   ❌ Assignments API failed"

# Clean up backend
kill $BACKEND_PID 2>/dev/null
cd ..

# Test 2: Frontend Build
echo "2️⃣ Testing Frontend Build..."
cd frontend
npm run build > /dev/null 2>&1 && echo "   ✅ Frontend builds successfully" || echo "   ❌ Frontend build failed"

# Test 3: Environment Variables
echo "3️⃣ Testing Environment Configuration..."
if [ -f ".env.local" ] && grep -q "VITE_API_URL" .env.local; then
    echo "   ✅ Environment variables configured"
else
    echo "   ❌ Environment variables missing"
fi

cd ..

# Test 4: Tests Pass
echo "4️⃣ Running All Tests..."
cd frontend && npm run test:run > /dev/null 2>&1 && echo "   ✅ Frontend tests pass" || echo "   ❌ Frontend tests fail"
cd ../backend && source .venv/bin/activate && python -m pytest test_main.py > /dev/null 2>&1 && echo "   ✅ Backend tests pass" || echo "   ❌ Backend tests fail"

echo ""
echo "🎉 Integration Test Complete!"
echo "   Ready for deployment to free tiers"