const authTabs = document.querySelectorAll('.tab');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const dashboardSection = document.getElementById('dashboardSection');
const adminSection = document.getElementById('adminSection');
const authBox = document.getElementById('authBox');
const welcomeMessage = document.getElementById('welcomeMessage');
const dashboardCards = document.getElementById('dashboardCards');
const weatherForecast = document.getElementById('weatherForecast');
const vegetationMap = document.getElementById('vegetationMap');
const growthChart = document.getElementById('growthChart');
const threatList = document.getElementById('threatList');
const recommendationSummary = document.getElementById('recommendationSummary');
const adminStats = document.getElementById('adminStats');
const diseaseForm = document.getElementById('diseaseForm');
const diseaseImageInput = document.getElementById('diseaseImage');
const diseaseResult = document.getElementById('diseaseResult');
const cropRecommendationForm = document.getElementById('cropRecommendationForm');
const recommendationResult = document.getElementById('recommendationResult');
const farmMapElement = document.getElementById('farmMap');
const mapStatus = document.getElementById('mapStatus');
const latitudeInput = cropRecommendationForm.querySelector('[name="latitude"]');
const longitudeInput = cropRecommendationForm.querySelector('[name="longitude"]');
let farmMap;
let farmMarker;

const api = {
  get: async (path) => {
    const response = await fetch(path);
    if (!response.ok) {
      throw new Error('Request failed');
    }
    return response.json();
  },
  post: async (path, body) => {
    const response = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Request failed');
    }
    return response.json();
  }
};

const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
}[character]));

const toneClassMap = {
  green: 'green',
  blue: 'blue',
  amber: 'amber',
  red: 'red',
  teal: 'teal',
  purple: 'purple'
};

const showTab = (tabName) => {
  authTabs.forEach((tab) => {
    const isActive = tab.dataset.tab === tabName;
    tab.classList.toggle('active', isActive);
  });

  loginForm.classList.toggle('active', tabName === 'login');
  registerForm.classList.toggle('active', tabName === 'register');
};

const renderDashboard = (dashboard, weather, vegetation, threats, fertilizer, yieldData, water) => {
  welcomeMessage.textContent = dashboard.welcome;

  dashboardCards.innerHTML = dashboard.cards.map((card) => `
    <div class="stat-card ${toneClassMap[card.tone] || 'green'}">
      <h4>${card.title}</h4>
      <div class="value">${card.value}</div>
      <div class="detail">${card.detail}</div>
    </div>
  `).join('');

  weatherForecast.innerHTML = weather.forecast.map((day) => `
    <div class="forecast-item">
      <span>${day.day}</span>
      <strong>${day.icon} ${day.temp}°C</strong>
      <span>${day.rain} mm</span>
    </div>
  `).join('');

  vegetationMap.innerHTML = vegetation.map.map((zone) => `
    <div class="veg-item">
      <span>${zone.zone}</span>
      <span>${zone.value.toFixed(2)}</span>
      <span class="badge">${zone.label}</span>
    </div>
  `).join('');

  const growthBars = [52, 64, 77, 84, 92, 88, 94];
  growthChart.innerHTML = growthBars.map((value, index) => `
    <div class="bar-col">
      <div class="bar" style="height: ${value}%"></div>
      <div class="bar-label">${['Jun','Jul','Aug','Sep','Oct','Nov','Dec'][index]}</div>
    </div>
  `).join('');

  threatList.innerHTML = threats.threats.map((item) => `
    <div class="list-item">
      <strong>${item.name}</strong>
      <p><b>Risk:</b> ${item.risk} · <b>Crop:</b> ${item.crop}</p>
      <p>${item.evidence}</p>
    </div>
  `).join('');

  recommendationSummary.innerHTML = `
    <div><strong>Weather:</strong> ${weather.analysis[0]}</div>
    <div><strong>Water:</strong> ${water.recommendation}</div>
    <div><strong>Fertilizer:</strong> ${fertilizer.recommendations[0].name} • ${fertilizer.recommendations[0].purpose}</div>
    <div><strong>Yield:</strong> Expected production is ${yieldData.expectedYieldPerAcre} per acre with a ${yieldData.performance.toLowerCase()} performance outlook.</div>
  `;
};

const renderAdminStats = (adminData) => {
  const stats = [
    { label: 'Registered farmers', value: adminData.farmers },
    { label: 'Active farms', value: adminData.activeFarms },
    { label: 'Risk alerts', value: adminData.riskAlerts },
    { label: 'Weather stations', value: adminData.weatherStations },
    { label: 'Disease models', value: adminData.diseaseModels },
    { label: 'Reports generated', value: adminData.reportsGenerated }
  ];

  adminStats.innerHTML = stats.map((item) => `
    <div class="admin-card">
      <h4>${item.label}</h4>
      <strong>${item.value}</strong>
    </div>
  `).join('');
};

const showDashboard = async () => {
  try {
    const [dashboard, weather, vegetation, threats, fertilizer, yieldData, water, admin] = await Promise.all([
      api.get('/api/dashboard'),
      api.get('/api/weather'),
      api.get('/api/vegetation'),
      api.get('/api/threats'),
      api.get('/api/fertilizer'),
      api.get('/api/yield'),
      api.get('/api/water'),
      api.get('/api/admin')
    ]);

    renderDashboard(dashboard, weather, vegetation, threats, fertilizer, yieldData, water);
    renderAdminStats(admin);
    dashboardSection.classList.remove('hidden');
    adminSection.classList.remove('hidden');
    authBox.classList.add('hidden');
    window.setTimeout(() => farmMap?.invalidateSize(), 60);
  } catch (error) {
    alert('Unable to load dashboard data in demo mode.');
  }
};

const login = async (event) => {
  event.preventDefault();
  const formData = new FormData(loginForm);
  const payload = {
    mobile: formData.get('mobile'),
    password: formData.get('password')
  };

  try {
    await api.post('/api/auth/login', payload);
    showDashboard();
  } catch (error) {
    alert(error.message || 'Invalid credentials');
  }
};

const register = async (event) => {
  event.preventDefault();
  const formData = new FormData(registerForm);
  const payload = {
    fullName: formData.get('fullName'),
    mobile: formData.get('mobile'),
    email: formData.get('email'),
    password: formData.get('password'),
    state: formData.get('state'),
    district: formData.get('district'),
    village: formData.get('village'),
    farmName: formData.get('farmName')
  };

  try {
    await api.post('/api/auth/register', payload);
    alert('Registration successful. You are now in demo mode.');
    showTab('login');
  } catch (error) {
    alert(error.message || 'Unable to register');
  }
};

const resetPassword = async (event) => {
  event.preventDefault();
  const mobile = document.querySelector('#loginForm input[name="mobile"]').value;
  try {
    const result = await api.post('/api/auth/forgot-password', { mobile });
    alert(result.message);
  } catch (error) {
    alert(error.message || 'Unable to reset password');
  }
};

const logout = () => {
  dashboardSection.classList.add('hidden');
  adminSection.classList.add('hidden');
  authBox.classList.remove('hidden');
  showTab('login');
};

const analyzeDisease = async (event) => {
  event.preventDefault();
  const file = diseaseImageInput.files[0];

  if (!file) {
    diseaseResult.textContent = 'Please select a crop image from the camera or gallery.';
    return;
  }

  const formData = new FormData();
  formData.append('file', file);
  const cropMetadata = new FormData(cropRecommendationForm);
  formData.append('cropName', cropMetadata.get('cropName') || 'General crop');
  formData.append('state', cropMetadata.get('state') || 'Karnataka');
  formData.append('district', cropMetadata.get('district') || 'Mysuru');
  formData.append('village', cropMetadata.get('village') || 'Hunsur');
  formData.append('latitude', cropMetadata.get('latitude') || 12.3);
  formData.append('longitude', cropMetadata.get('longitude') || 76.6);

  diseaseResult.textContent = 'Analyzing crop image...';

  try {
    const response = await fetch('/api/disease/analyze', {
      method: 'POST',
      body: formData
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || 'Disease analysis failed.');
    }

    const { predictedDisease, confidencePct, severity, treatment, prevention, warning, cropName, location } = result.result;
    diseaseResult.innerHTML = `
      <strong>Crop:</strong> ${escapeHtml(cropName)}<br>
      <strong>Farm location:</strong> ${escapeHtml(location.village)}, ${escapeHtml(location.district)}, ${escapeHtml(location.state)} (${location.coordinates.latitude}, ${location.coordinates.longitude})<br>
      <strong>Prediction:</strong> ${escapeHtml(predictedDisease)}<br>
      <strong>Confidence:</strong> ${confidencePct}%<br>
      <strong>Severity:</strong> ${escapeHtml(severity)}<br>
      <strong>Recommended treatment:</strong> ${escapeHtml(treatment)}<br>
      <strong>Prevention:</strong> ${escapeHtml(prevention)}<br>
      <small>${escapeHtml(warning)}</small>
    `;
  } catch (error) {
    diseaseResult.textContent = error.message || 'Unable to analyze the uploaded crop image.';
  }
};

const generateRecommendation = async (event) => {
  event.preventDefault();
  const formData = new FormData(cropRecommendationForm);
  const payload = {
    fullName: formData.get('fullName') || 'Farm owner',
    cropName: formData.get('cropName'),
    state: formData.get('state') || 'Karnataka',
    district: formData.get('district') || 'Mysuru',
    village: formData.get('village') || 'Hunsur',
    season: formData.get('season') || 'Kharif',
    soilType: formData.get('soilType') || 'Loam',
    landArea: Number(formData.get('landArea') || 1),
    latitude: Number(formData.get('latitude') || 12.3),
    longitude: Number(formData.get('longitude') || 76.6),
    rainfall: Number(formData.get('rainfall') || 750),
    humidity: Number(formData.get('humidity') || 68),
    temperature: Number(formData.get('temperature') || 28)
  };

  recommendationResult.textContent = 'Generating the crop recommendation model output...';

  try {
    const response = await fetch('/api/farm/recommendation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || 'Recommendation failed.');
    }

    const { crop, requestedCrop, suitability, confidencePct, locationZone, reason, irrigationAdvice, fertilizerAdvice, risk, yieldExpectation, datasetNotice } = result.recommendation;
    recommendationResult.innerHTML = `
      <strong>Crop entered:</strong> ${escapeHtml(requestedCrop)}<br>
      <strong>Model suggestion:</strong> ${escapeHtml(crop)} (${escapeHtml(suitability)})<br>
      <strong>Confidence:</strong> ${confidencePct}%<br>
      <strong>Farm:</strong> ${escapeHtml(result.location.village)}, ${escapeHtml(result.location.district)}, ${escapeHtml(result.location.state)}<br>
      <strong>Location zone:</strong> ${escapeHtml(locationZone)}<br>
      <strong>Why this crop:</strong> ${escapeHtml(reason)}<br>
      <strong>Irrigation:</strong> ${escapeHtml(irrigationAdvice)}<br>
      <strong>Fertilizer:</strong> ${escapeHtml(fertilizerAdvice)}<br>
      <strong>Risk:</strong> ${escapeHtml(risk)}<br>
      <strong>Yield expectation:</strong> ${escapeHtml(yieldExpectation)}<br>
      <small>${escapeHtml(datasetNotice)}</small>
    `;

    recommendationSummary.innerHTML = `
      <div><strong>Farmer:</strong> ${escapeHtml(result.farmer.name)}</div>
      <div><strong>Farm:</strong> ${escapeHtml(result.location.village)}, ${escapeHtml(result.location.district)}, ${escapeHtml(result.location.state)}</div>
      <div><strong>Crop entered:</strong> ${escapeHtml(requestedCrop)}</div>
      <div><strong>Model suggestion:</strong> ${escapeHtml(crop)} (${escapeHtml(suitability)})</div>
      <div><strong>Confidence:</strong> ${confidencePct}%</div>
      <div><strong>Guidance:</strong> ${escapeHtml(irrigationAdvice)}</div>
    `;
  } catch (error) {
    recommendationResult.textContent = error.message || 'Unable to generate crop recommendation.';
  }
};

const setFarmCoordinates = (latitude, longitude, source) => {
  latitudeInput.value = latitude.toFixed(6);
  longitudeInput.value = longitude.toFixed(6);
  if (farmMap && farmMarker) {
    const position = [latitude, longitude];
    farmMarker.setLatLng(position);
    farmMap.setView(position, Math.max(farmMap.getZoom(), 11));
  }
  mapStatus.textContent = `${source}: ${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
};

const initializeFarmMap = () => {
  if (!farmMapElement || !window.L) {
    mapStatus.textContent = 'Map tiles are unavailable. Enter the farm latitude and longitude manually.';
    return;
  }

  const initialPosition = [Number(latitudeInput.value) || 12.3, Number(longitudeInput.value) || 76.6];
  farmMap = window.L.map(farmMapElement).setView(initialPosition, 10);
  window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(farmMap);
  farmMarker = window.L.marker(initialPosition, { draggable: true }).addTo(farmMap);
  farmMap.on('click', (event) => setFarmCoordinates(event.latlng.lat, event.latlng.lng, 'Map pin'));
  farmMarker.on('dragend', (event) => {
    const position = event.target.getLatLng();
    setFarmCoordinates(position.lat, position.lng, 'Moved pin');
  });
  farmMapElement.dataset.ready = 'true';
};

latitudeInput.addEventListener('change', () => {
  setFarmCoordinates(Number(latitudeInput.value), Number(longitudeInput.value), 'Coordinates');
});
longitudeInput.addEventListener('change', () => {
  setFarmCoordinates(Number(latitudeInput.value), Number(longitudeInput.value), 'Coordinates');
});
document.getElementById('locateFarmButton').addEventListener('click', () => {
  if (!navigator.geolocation) {
    mapStatus.textContent = 'Location services are not available in this browser.';
    return;
  }
  mapStatus.textContent = 'Requesting location permission...';
  navigator.geolocation.getCurrentPosition(
    ({ coords }) => setFarmCoordinates(coords.latitude, coords.longitude, 'Device location'),
    () => { mapStatus.textContent = 'Location permission was not granted. Choose a map point or enter coordinates.'; },
    { enableHighAccuracy: true, timeout: 10000 }
  );
});

const primaryAction = document.getElementById('startButton');
const primarySecondary = document.getElementById('ctaPrimary');
const loginButton = document.getElementById('loginButton');
const ctaSecondary = document.getElementById('ctaSecondary');
const logoutButton = document.getElementById('logoutButton');
const forgotPassword = document.getElementById('forgotPassword');

authTabs.forEach((tab) => tab.addEventListener('click', () => showTab(tab.dataset.tab)));
loginForm.addEventListener('submit', login);
registerForm.addEventListener('submit', register);
forgotPassword.addEventListener('click', resetPassword);
logoutButton.addEventListener('click', logout);
diseaseForm.addEventListener('submit', analyzeDisease);
cropRecommendationForm.addEventListener('submit', generateRecommendation);
initializeFarmMap();

[primaryAction, primarySecondary, loginButton, ctaSecondary].forEach((button) => {
  button.addEventListener('click', () => {
    dashboardSection.classList.add('hidden');
    adminSection.classList.add('hidden');
    authBox.classList.remove('hidden');
    showTab('login');
    window.scrollTo({ top: document.querySelector('.auth-section').offsetTop - 30, behavior: 'smooth' });
  });
});

showTab('login');
