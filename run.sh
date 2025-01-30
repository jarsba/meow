#!/bin/bash

# Start the frontend
npm run dev &

# Start the backend
python3 -m backend.app &

# Start the ml
python3 -m ml.meow &

echo "All services started"
echo "Open http://localhost:3000 to use the web-application"