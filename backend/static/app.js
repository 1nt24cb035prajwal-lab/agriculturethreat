const authTabs = document.querySelectorAll('.tab');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const dashboardSection = document.getElementById('dashboardSection');
const adminSection = document.getElementById('adminSection');
const authBox = document.getElementById('authBox');
const welcomeMessage = document.getElementById('welcomeMessage');
const farmerProfileSummary = document.getElementById('farmerProfileSummary');
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
const activityHistory = document.getElementById('activityHistory');
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
  },
  put: async (path, body) => {
    const response = await fetch(path, {
      method: 'PUT',
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

const renderDashboard = (dashboard) => {
  const { farmer, farm, integrations } = dashboard;
  welcomeMessage.textContent = dashboard.welcome;
  farmerProfileSummary.textContent = `${farmer.email} · ${farm.farmName || 'Farm details not yet saved'}`;
  const location = [farm.village, farm.district, farm.state].filter(Boolean).join(', ') || 'Not set';
  const cards = [
    { title: 'Current crop', value: farm.cropName || 'Not set', detail: 'Saved farmer input', tone: 'green' },
    { title: 'Farm area', value: farm.landArea ? `${farm.landArea} ${farm.landAreaUnit || 'acres'}` : 'Not set', detail: 'Saved farm profile', tone: 'blue' },
    { title: 'Farm location', value: location, detail: farm.latitude == null ? 'Choose a map location' : `${farm.latitude}, ${farm.longitude}`, tone: 'teal' },
    { title: 'Soil type', value: farm.soilType || 'Not set', detail: 'Farmer supplied', tone: 'green' },
    { title: 'Weather', value: integrations.weather === 'not_configured' ? 'Not connected' : 'Unavailable', detail: 'No live weather provider', tone: 'amber' },
    { title: 'Satellite / NDVI', value: 'Not connected', detail: 'No satellite provider', tone: 'blue' },
    { title: 'Market prices', value: 'Not connected', detail: 'No market data provider', tone: 'purple' },
    { title: 'Live threat alerts', value: 'Unavailable', detail: 'No verified live threat feed', tone: 'red' }
  ];
  dashboardCards.innerHTML = cards.map((card) => `
    <div class="stat-card ${toneClassMap[card.tone] || 'green'}">
      <h4>${escapeHtml(card.title)}</h4>
      <div class="value">${escapeHtml(card.value)}</div>
      <div class="detail">${escapeHtml(card.detail)}</div>
    </div>
  `).join('');

  weatherForecast.innerHTML = '<p class="empty-state">A weather provider has not been configured. No forecast is available.</p>';
  vegetationMap.innerHTML = '<p class="empty-state">Satellite imagery and NDVI are not connected. No vegetation measurement is available.</p>';
  growthChart.innerHTML = '<p class="empty-state">Yield history will appear after real or farmer-recorded yield data is saved.</p>';
  threatList.innerHTML = '<p class="empty-state">No live threat feed is connected. This page will not invent risk alerts.</p>';
  recommendationSummary.innerHTML = `
    <div><strong>Farm:</strong> ${escapeHtml(farm.farmName || 'Not saved')}</div>
    <div><strong>Crop:</strong> ${escapeHtml(farm.cropName || 'Not set')}</div>
    <div><strong>Location:</strong> ${escapeHtml(location)}</div>
    <div><strong>Water, yield, and fertilizer:</strong> No validated local data is connected. Use the crop recommendation as a clearly labeled prototype estimate only.</div>
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
    const [dashboard, history] = await Promise.all([
      api.get('/api/dashboard'),
      api.get('/api/activity')
    ]);

    renderDashboard(dashboard);
    fillFarmForm(dashboard.farm || {});
    renderActivity(history.items);
    dashboardSection.classList.remove('hidden');
    adminSection.classList.add('hidden');
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
    identifier: formData.get('identifier'),
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
  if (formData.get('password') !== formData.get('confirmPassword')) {
    alert('Passwords do not match.');
    return;
  }
  const payload = {
    fullName: formData.get('fullName'),
    mobile: formData.get('mobile'),
    email: formData.get('email'),
    password: formData.get('password'),
    state: formData.get('state'),
    district: formData.get('district'),
    village: formData.get('village'),
    farmName: formData.get('farmName'),
    termsAccepted: formData.get('termsAccepted') === 'on'
  };

  try {
    const result = await api.post('/api/auth/register', payload);
    document.querySelector('#loginForm [name="identifier"]').value = payload.mobile;
    alert(`${result.message} Sign in with your phone or email and password.`);
    showTab('login');
  } catch (error) {
    alert(error.message || 'Unable to register');
  }
};

const resetPassword = async (event) => {
  event.preventDefault();
  const identifier = document.querySelector('#loginForm input[name="identifier"]').value;
  try {
    const result = await api.post('/api/auth/forgot-password', { identifier });
    alert(result.message);
  } catch (error) {
    alert(error.message || 'Unable to reset password');
  }
};

const logout = () => {
  api.post('/api/auth/logout', {}).catch(() => {});
  dashboardSection.classList.add('hidden');
  adminSection.classList.add('hidden');
  authBox.classList.remove('hidden');
  showTab('login');
};

const fillFarmForm = (farm) => {
  const form = cropRecommendationForm;
  for (const [name, value] of Object.entries(farm)) {
    const input = form.elements.namedItem(name);
    if (input && value !== null && value !== undefined && value !== '') {
      input.value = value;
    }
  }
  if (farm.latitude !== null && farm.latitude !== undefined && farm.longitude !== null && farm.longitude !== undefined) {
    setFarmCoordinates(Number(farm.latitude), Number(farm.longitude), 'Saved farm location');
  }
};

const renderActivity = (items) => {
  if (!items.length) {
    activityHistory.innerHTML = '<p>No saved activity yet.</p>';
    return;
  }
  activityHistory.innerHTML = items.map((item) => `
    <div class="list-item">
      <strong>${escapeHtml(item.type.replaceAll('_', ' '))}</strong>
      <p>${escapeHtml(JSON.stringify(item.details))}</p>
      ${item.details.imageId ? `<img class="activity-image" src="/api/disease/history/${encodeURIComponent(item.details.imageId)}/image" alt="Saved crop disease image" loading="lazy">` : ''}
      <small>${new Date(item.createdAt * 1000).toLocaleString()}</small>
    </div>
  `).join('');
};

const farmerFormPayload = () => {
  const data = new FormData(cropRecommendationForm);
  return {
    farmName: data.get('farmName'),
    cropName: data.get('cropName'),
    state: data.get('state'),
    district: data.get('district'),
    village: data.get('village'),
    cropVariety: data.get('cropVariety'),
    cropStage: data.get('cropStage'),
    farmingMethod: data.get('farmingMethod'),
    previousCrop: data.get('previousCrop'),
    cultivationStart: data.get('cultivationStart'),
    expectedHarvest: data.get('expectedHarvest'),
    soilType: data.get('soilType'),
    irrigationType: data.get('irrigationType'),
    waterSource: data.get('waterSource'),
    season: data.get('season'),
    landArea: Number(data.get('landArea')),
    landAreaUnit: data.get('landAreaUnit'),
    soilPh: data.get('soilPh') ? Number(data.get('soilPh')) : null,
    nitrogen: data.get('nitrogen') ? Number(data.get('nitrogen')) : null,
    phosphorus: data.get('phosphorus') ? Number(data.get('phosphorus')) : null,
    potassium: data.get('potassium') ? Number(data.get('potassium')) : null,
    soilMoisture: data.get('soilMoisture') ? Number(data.get('soilMoisture')) : null,
    organicCarbon: data.get('organicCarbon') ? Number(data.get('organicCarbon')) : null,
    rainfall: Number(data.get('rainfall')),
    humidity: Number(data.get('humidity')),
    temperature: Number(data.get('temperature')),
    latitude: Number(data.get('latitude')),
    longitude: Number(data.get('longitude'))
  };
};

const saveFarmProfile = async () => {
  const result = await api.put('/api/farm/profile', farmerFormPayload());
  farmerProfileSummary.textContent = `${result.farm.farmName} · ${result.farm.village}, ${result.farm.district}, ${result.farm.state}`;
  const history = await api.get('/api/activity');
  renderActivity(history.items);
  return result;
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
    renderActivity((await api.get('/api/activity')).items);
  } catch (error) {
    diseaseResult.textContent = error.message || 'Unable to analyze the uploaded crop image.';
  }
};

const generateRecommendation = async (event) => {
  event.preventDefault();
  const payload = farmerFormPayload();

  recommendationResult.textContent = 'Generating the crop recommendation model output...';

  try {
    await api.put('/api/farm/profile', payload);
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
    renderActivity((await api.get('/api/activity')).items);
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
  } else if (farmMap) {
    const position = [latitude, longitude];
    farmMarker = window.L.marker(position, { draggable: true }).addTo(farmMap);
    farmMarker.on('dragend', (event) => {
      const movedTo = event.target.getLatLng();
      setFarmCoordinates(movedTo.lat, movedTo.lng, 'Moved pin');
    });
    farmMap.setView(position, 11);
  }
  mapStatus.textContent = `${source}: ${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
};

const initializeFarmMap = () => {
  if (!farmMapElement || !window.L) {
    mapStatus.textContent = 'Map tiles are unavailable. Enter the farm latitude and longitude manually.';
    return;
  }

  const hasSavedLocation = latitudeInput.value !== '' && longitudeInput.value !== '';
  const initialPosition = hasSavedLocation
    ? [Number(latitudeInput.value), Number(longitudeInput.value)]
    : [20.5937, 78.9629];
  farmMap = window.L.map(farmMapElement).setView(initialPosition, hasSavedLocation ? 10 : 4);
  window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(farmMap);
  if (hasSavedLocation) {
    farmMarker = window.L.marker(initialPosition, { draggable: true }).addTo(farmMap);
    farmMarker.on('dragend', (event) => {
      const position = event.target.getLatLng();
      setFarmCoordinates(position.lat, position.lng, 'Moved pin');
    });
  }
  farmMap.on('click', (event) => setFarmCoordinates(event.latlng.lat, event.latlng.lng, 'Map pin'));
  farmMapElement.dataset.ready = 'true';
};

const syncFarmCoordinatesFromInputs = () => {
  if (!latitudeInput.value.trim() || !longitudeInput.value.trim()) {
    return;
  }
  const latitude = Number(latitudeInput.value);
  const longitude = Number(longitudeInput.value);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180) {
    mapStatus.textContent = 'Enter a valid latitude and longitude.';
    return;
  }
  setFarmCoordinates(latitude, longitude, 'Coordinates');
};

latitudeInput.addEventListener('change', syncFarmCoordinatesFromInputs);
longitudeInput.addEventListener('change', syncFarmCoordinatesFromInputs);
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
document.getElementById('saveFarmButton').addEventListener('click', async () => {
  try {
    const result = await saveFarmProfile();
    recommendationResult.textContent = `Saved farm profile for ${result.farm.farmName}.`;
  } catch (error) {
    recommendationResult.textContent = error.message || 'Unable to save farm profile.';
  }
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

diseaseImageInput.addEventListener('change', () => {
  const image = diseaseImageInput.files[0];
  const preview = document.getElementById('diseasePreview');
  const removeButton = document.getElementById('removeDiseaseImage');
  if (!image) {
    preview.classList.add('hidden');
    removeButton.classList.add('hidden');
    preview.removeAttribute('src');
    return;
  }
  preview.src = URL.createObjectURL(image);
  preview.classList.remove('hidden');
  removeButton.classList.remove('hidden');
});

document.getElementById('removeDiseaseImage').addEventListener('click', () => {
  diseaseImageInput.value = '';
  diseaseImageInput.dispatchEvent(new Event('change'));
});

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
