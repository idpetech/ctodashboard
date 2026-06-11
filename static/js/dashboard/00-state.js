/* CTO Lens dashboard module: 00-state.js */
// Authentication State Management
let currentUser = null;
let authToken = null;
let isAuthenticated = false;
let assignments = []; // Store assignments globally for management functions
let trialState = null;
