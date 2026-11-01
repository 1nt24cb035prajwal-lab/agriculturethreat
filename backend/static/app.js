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
let weatherPreviewTimer;
let dashboardData;

const api = {
  get: async (path) => {
    const response = await fetch(path);
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Request failed');
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

const renderDashboard = (dashboard, weather = null, water = null) => {
  const { farmer, farm, integrations } = dashboard;
  welcomeMessage.textContent = dashboard.welcome;
  farmerProfileSummary.textContent = `${farmer.email} · ${farm.farmName || 'Farm details not yet saved'}`;
  const location = [farm.village, farm.district, farm.state].filter(Boolean).join(', ') || 'Not set';
  const cards = [
    { title: 'Current crop', value: farm.cropName || 'Not set', detail: 'Saved farmer input', tone: 'green' },
    { title: 'Farm area', value: farm.landArea ? `${farm.landArea} ${farm.landAreaUnit || 'acres'}` : 'Not set', detail: 'Saved farm profile', tone: 'blue' },
    { title: 'Farm location', value: location, detail: farm.latitude == null ? 'Choose a map location' : `${farm.latitude}, ${farm.longitude}`, tone: 'teal' },
    { title: 'Soil type', value: farm.soilType || 'Not set', detail: 'Farmer supplied', tone: 'green' },
    { title: 'Weather', value: weather ? `${weather.current.temperatureC}°C · ${weather.current.condition}` : 'Unavailable', detail: weather ? `${weather.current.humidityPercent}% humidity · ${weather.current.rainfallMm} mm rain` : 'Live weather unavailable', tone: 'amber' },
    { title: 'Water requirement', value: water ? `${water.dailyIrrigationLitersEstimate} L/day est.` : 'Unavailable', detail: water ? `${water.nextSevenDaysLitersEstimate} L / 7-day estimate` : 'Needs crop, area, and live ET0', tone: 'teal' },
    { title: 'Satellite / NDVI', value: integrations.satellite === 'configured' ? 'Sentinel Hub ready' : 'Needs credentials', detail: 'Sentinel-2 point sample', tone: 'blue' },
    { title: 'Market prices', value: integrations.marketPrices === 'configured' ? 'Agmarknet API ready' : 'Needs API key', detail: 'data.gov.in mandi arrivals', tone: 'purple' },
    { title: 'Live threat alerts', value: 'Unavailable', detail: 'No verified live threat feed', tone: 'red' }
  ];
  dashboardCards.innerHTML = cards.map((card) => `
    <div class="stat-card ${toneClassMap[card.tone] || 'green'}">
      <h4>${escapeHtml(card.title)}</h4>
      <div class="value">${escapeHtml(card.value)}</div>
      <div class="detail">${escapeHtml(card.detail)}</div>
    </div>
  `).join('');

  renderWeatherForecast(weather);
  vegetationMap.innerHTML = '<p class="empty-state">Satellite imagery and NDVI are not connected. No vegetation measurement is available.</p>';
  growthChart.innerHTML = '<p class="empty-state">Yield history will appear after real or farmer-recorded yield data is saved.</p>';
  threatList.innerHTML = '<p class="empty-state">No live threat feed is connected. This page will not invent risk alerts.</p>';
  recommendationSummary.innerHTML = `
    <div><strong>Farm:</strong> ${escapeHtml(farm.farmName || 'Not saved')}</div>
    <div><strong>Crop:</strong> ${escapeHtml(farm.cropName || 'Not set')}</div>
    <div><strong>Location:</strong> ${escapeHtml(location)}</div>
    <div id="waterEstimateDetails"><strong>Water requirement:</strong> ${water ? `${escapeHtml(water.dailyIrrigationLitersEstimate)} L/day · ${escapeHtml(water.nextSevenDaysLitersEstimate)} L over 7 days` : 'Save crop, area, and map coordinates for an estimate.'}</div>
    ${water ? `<small>${escapeHtml(water.notice)}</small>` : ''}
    <div><strong>Yield and soil-test fertilizer:</strong> No validated regional yield or soil-test data is connected.</div>
  `;
  document.getElementById('settingsSummary').innerHTML = `
    <div><strong>Farmer:</strong> ${escapeHtml(farmer.name)}</div>
    <div><strong>Email:</strong> ${escapeHtml(farmer.email)}</div>
    <div><strong>Phone:</strong> ${escapeHtml(farmer.mobile || 'Not provided')} · ${farmer.phoneVerified ? 'Verified' : 'Not provided'}</div>
    <div><strong>Farm:</strong> ${escapeHtml(farm.farmName || 'Not saved')}</div>
    <div><strong>Location:</strong> ${escapeHtml(location)}</div>
  `;
};

const renderWeatherForecast = (weather) => {
  weatherForecast.innerHTML = weather?.forecast?.length
    ? weather.forecast.map((day) => `
      <div class="forecast-item">
        <span>${escapeHtml(day.date)}</span>
        <strong>${escapeHtml(day.condition)} · ${escapeHtml(day.temperatureMinC)}–${escapeHtml(day.temperatureMaxC)}°C</strong>
        <span>${escapeHtml(day.rainProbabilityPercent ?? '—')}% rain</span>
      </div>
    `).join('') + `<small class="data-source">Source: ${escapeHtml(weather.source)} · Updated ${escapeHtml(weather.retrievedAt)}</small>`
    : '<p class="empty-state">No live forecast is available for this saved farm location.</p>';
};

const loadYieldEstimate = async () => {
  const output = document.getElementById('yieldResult');
  if (!output) return;
  output.textContent = 'Calculating an indicative yield range...';
  try {
    const result = await api.get('/api/yield');
    output.innerHTML = `<strong>Crop:</strong> ${escapeHtml(result.crop)}<br><strong>Expected estimate:</strong> ${escapeHtml(result.expectedEstimateTonnes)} tonnes<br><strong>Range:</strong> ${escapeHtml(result.lowEstimateTonnes)}–${escapeHtml(result.highEstimateTonnes)} tonnes<br><strong>Area:</strong> ${escapeHtml(result.areaHectares)} ha<br><strong>Confidence:</strong> ${escapeHtml(result.confidence)}<br><small>${escapeHtml(result.notice)}</small>`;
  } catch (error) { output.textContent = error.message; }
};

const loadMarketPrices = async () => {
  const output = document.getElementById('marketResult');
  if (!output) return;
  const commodity = document.getElementById('marketCommodity').value.trim();
  output.textContent = 'Loading mandi arrivals...';
  try {
    const result = await api.get('/api/markets' + (commodity ? `?commodity=${encodeURIComponent(commodity)}` : ''));
    output.innerHTML = result.records.length ? result.records.map(row => `<div class="list-item"><strong>${escapeHtml(row.market || 'Market')}</strong><p>${escapeHtml(row.commodity)} · ${escapeHtml(row.variety || 'Variety not stated')} · ${escapeHtml(row.arrivalDate || '')}</p><p>Min ₹${escapeHtml(row.minPriceRsPerQuintal)} · Modal ₹${escapeHtml(row.modalPriceRsPerQuintal)} · Max ₹${escapeHtml(row.maxPriceRsPerQuintal)} / quintal</p></div>`).join('') + `<small class="data-source">Source: ${escapeHtml(result.source)} · ${escapeHtml(result.retrievedAt)}</small>` : '<p>No matching market records were returned.</p>';
  } catch (error) { output.textContent = error.message; }
};

const loadSatelliteNdvi = async () => {
  const output = vegetationMap;
  if (!output) return;
  output.textContent = 'Requesting Sentinel-2 imagery sample...';
  try {
    const result = await api.get('/api/vegetation');
    output.innerHTML = `<strong>NDVI:</strong> ${escapeHtml(result.ndvi)}<p>Source: ${escapeHtml(result.source)} · ${escapeHtml(result.retrievedAt)}</p><small>${escapeHtml(result.notice)}</small>`;
  } catch (error) { output.textContent = error.message; }
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

    dashboardData = dashboard;
    renderDashboard(dashboard);
    fillFarmForm(dashboard.farm || {});
    const marketCommodityInput = document.getElementById('marketCommodity');
    if (marketCommodityInput && dashboard.farm?.cropName) marketCommodityInput.value = dashboard.farm.cropName;
    renderActivity(history.items);
    dashboardSection.classList.remove('hidden');
    adminSection.classList.add('hidden');
    authBox.classList.add('hidden');
    window.setTimeout(() => farmMap?.invalidateSize(), 60);
    const hasSavedCoordinates = dashboard.farm.latitude !== null && dashboard.farm.longitude !== null;
    const hasWaterInputs = Boolean(dashboard.farm.cropName && dashboard.farm.landArea);
    if (hasSavedCoordinates && hasWaterInputs) {
      refreshDashboardFeeds(dashboard);
    }
  } catch (error) {
    alert('Unable to load dashboard data in demo mode.');
  }
};

const refreshDashboardFeeds = async (dashboard) => {
  const [weatherResult, waterResult] = await Promise.allSettled([api.get('/api/weather'), api.get('/api/water')]);
  if (dashboardData?.farmer?.id !== dashboard.farmer.id || dashboardSection.classList.contains('hidden')) {
    return;
  }
  renderDashboard(
    dashboard,
    weatherResult.status === 'fulfilled' ? weatherResult.value : null,
    waterResult.status === 'fulfilled' ? waterResult.value : null
  );
};

const routeTitles = {
  dashboard: ['Farmer dashboard', 'Dashboard'],
  farm: ['Farm records', 'Crop and Land Information'],
  recommendations: ['Decision support', 'Crop Recommendation'],
  disease: ['Image review', 'Disease Detection'],
  weather: ['Open-Meteo', 'Weather Monitoring'],
  satellite: ['Provider unavailable', 'Satellite Vegetation'],
  yield: ['History only', 'Crop Yield'],
  threats: ['Provider unavailable', 'Threat Information'],
  history: ['Your account records', 'Activity History'],
  reports: ['Export saved records', 'Reports'],
  settings: ['Farmer account', 'Settings']
};

const navigateTo = (path, replace = false) => {
  if (replace) {
    window.history.replaceState({}, '', path);
  } else {
    window.history.pushState({}, '', path);
  }
  renderCurrentPage();
};

const renderCurrentPage = async () => {
  const requestedPage = window.location.pathname.replace(/^\/+|\/+$/g, '') || 'home';
  const publicPages = new Set(['home', 'login', 'register']);
  const page = routeTitles[requestedPage] || publicPages.has(requestedPage) ? requestedPage : 'home';
  document.body.dataset.page = page;
  adminSection.classList.add('hidden');

  if (page === 'home' || page === 'login' || page === 'register') {
    dashboardSection.classList.add('hidden');
    authBox.classList.remove('hidden');
    document.title = page === 'home' ? 'Agriculture Threat Fusion' : `${page === 'login' ? 'Farmer Login' : 'Farmer Registration'} | Agriculture Threat Fusion`;
    return;
  }

  try {
    await api.get('/api/me');
  } catch (error) {
    navigateTo('/login', true);
    return;
  }

  document.title = `${routeTitles[page][1]} | Agriculture Threat Fusion`;
  await showDashboard();
  const [eyebrow, title] = routeTitles[page];
  document.getElementById('pageEyebrow').textContent = eyebrow;
  document.getElementById('pageTitle').textContent = title;
  document.getElementById('farmPanelTitle').textContent = page === 'recommendations' ? 'Location and Crop Suitability Inputs' : 'Crop and Land Information';
  document.getElementById('historyPanelTitle').textContent = page === 'reports' ? 'Saved Activity Report' : 'Activity History';
  document.querySelectorAll('.farmer-navigation a').forEach((link) => {
    link.classList.toggle('active', link.pathname === `/${page}`);
  });
  document.querySelector('[data-feature-view~="settings"]').classList.toggle('hidden', page !== 'settings');
  document.getElementById('downloadReportButton').classList.toggle('hidden', page !== 'reports');
  if (page === 'yield') { loadYieldEstimate(); loadMarketPrices(); }
  if (page === 'satellite') loadSatelliteNdvi();
};

const logout = () => {
  api.post('/api/auth/logout', {}).catch(() => {});
  dashboardSection.classList.add('hidden');
  adminSection.classList.add('hidden');
  authBox.classList.remove('hidden');
  navigateTo('/login');
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
  let weather = null;
  let water = null;
  try {
    weather = await api.get('/api/weather');
  } catch (error) {
    weather = null;
  }
  try {
    water = await api.get('/api/water');
  } catch (error) {
    water = null;
  }
  renderDashboard(await api.get('/api/dashboard'), weather, water);
  fillFarmForm(result.farm);
  const history = await api.get('/api/activity');
  renderActivity(history.items);
  return result;
};

const analyzeDisease = async (event) => {
  event.preventDefault();
  const file = diseaseImageInput.files[0];
  const savedCrop = cropRecommendationForm.elements.namedItem('cropName').value;
  const diseaseCropInput = document.getElementById('diseaseCropName');
  if (!diseaseCropInput.value.trim() && savedCrop) diseaseCropInput.value = savedCrop;

  if (!file) {
    diseaseResult.textContent = 'Please select a crop image from the camera or gallery.';
    return;
  }

  const formData = new FormData();
  formData.append('file', file);
  const cropMetadata = new FormData(cropRecommendationForm);
  const diseaseCropName = document.getElementById('diseaseCropName').value.trim() || cropMetadata.get('cropName') || '';
  const diseaseCropStage = document.getElementById('diseaseCropStage').value;
  if (diseaseCropName) formData.append('cropName', diseaseCropName);
  if (diseaseCropStage) formData.append('cropStage', diseaseCropStage);
  for (const field of ['state', 'district', 'village', 'latitude', 'longitude']) {
    const value = cropMetadata.get(field);
    if (value !== null && String(value).trim() !== '') formData.append(field, value);
  }

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

    const { crop, requestedCrop, suitability, confidencePct, locationZone, reason, irrigationAdvice, fertilizerAdvice, risk, yieldExpectation, datasetNotice, alternatives = [] } = result.recommendation;
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
      <strong>Other suitable model candidates:</strong> ${alternatives.map(item => `${escapeHtml(item.crop)} (${escapeHtml(item.confidencePct)}%)`).join(', ')}<br>
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
  if (source !== 'Saved farm location') {
    window.clearTimeout(weatherPreviewTimer);
    weatherPreviewTimer = window.setTimeout(() => refreshWeatherForCoordinates(latitude, longitude), 500);
  }
};

const refreshWeatherForCoordinates = async (latitude, longitude) => {
  mapStatus.textContent = `Loading weather for ${latitude.toFixed(4)}, ${longitude.toFixed(4)}...`;
  try {
    const weather = await api.get(`/api/weather/preview?latitude=${encodeURIComponent(latitude)}&longitude=${encodeURIComponent(longitude)}`);
    renderWeatherForecast(weather);
    const liveTemperature = cropRecommendationForm.elements.namedItem('temperature');
    const liveHumidity = cropRecommendationForm.elements.namedItem('humidity');
    if (liveTemperature && weather.current.temperatureC != null) liveTemperature.value = weather.current.temperatureC;
    if (liveHumidity && weather.current.humidityPercent != null) liveHumidity.value = weather.current.humidityPercent;
    const weatherCard = [...dashboardCards.querySelectorAll('.stat-card')].find((card) => card.querySelector('h4')?.textContent === 'Weather');
    if (weatherCard) {
      weatherCard.querySelector('.value').textContent = `${weather.current.temperatureC}°C · ${weather.current.condition}`;
      weatherCard.querySelector('.detail').textContent = `${weather.current.humidityPercent}% humidity · ${weather.current.rainfallMm} mm rain · ${weather.source}`;
    }
    mapStatus.textContent = `Weather loaded from ${weather.source}; save the farm profile to keep this location.`;
  } catch (error) {
    mapStatus.textContent = error.message || 'Weather is unavailable for this selected location.';
  }
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

document.getElementById('searchLocationButton').addEventListener('click', async () => {
  const query = document.getElementById('locationSearchInput').value.trim();
  if (query.length < 3) {
    mapStatus.textContent = 'Enter at least 3 characters to search for a place.';
    return;
  }
  mapStatus.textContent = 'Searching OpenStreetMap locations...';
  try {
    const response = await api.get(`/api/location/search?q=${encodeURIComponent(query)}`);
    if (!response.results.length) {
      mapStatus.textContent = 'No matching places found. Move the map or enter coordinates manually.';
      return;
    }
    const place = response.results[0];
    setFarmCoordinates(place.latitude, place.longitude, 'Place search');
    applyPlaceDetails(place);
  } catch (error) {
    mapStatus.textContent = error.message || 'Place search is unavailable.';
  }
});

document.getElementById('lookupLocationButton').addEventListener('click', async () => {
  if (!latitudeInput.value || !longitudeInput.value) {
    mapStatus.textContent = 'Select the farm point on the map or use device location first.';
    return;
  }
  mapStatus.textContent = 'Identifying selected place...';
  try {
    const place = await api.post('/api/location/reverse', {
      latitude: Number(latitudeInput.value),
      longitude: Number(longitudeInput.value)
    });
    applyPlaceDetails(place);
    mapStatus.textContent = `${place.displayName} · OpenStreetMap`;
  } catch (error) {
    mapStatus.textContent = error.message || 'Place identification is unavailable.';
  }
});

const applyPlaceDetails = (place) => {
  for (const [field, value] of Object.entries({ village: place.village, district: place.district, state: place.state })) {
    if (value) {
      cropRecommendationForm.elements.namedItem(field).value = value;
    }
  }
};

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

document.getElementById('googleLoginButton').addEventListener('click', () => { window.location.href = '/auth/google/start'; });
document.getElementById('loadYieldButton').addEventListener('click', loadYieldEstimate);
document.getElementById('loadMarketsButton').addEventListener('click', loadMarketPrices);
document.getElementById('loadSatelliteButton').addEventListener('click', loadSatelliteNdvi);

logoutButton.addEventListener('click', logout);
diseaseForm.addEventListener('submit', analyzeDisease);
cropRecommendationForm.addEventListener('submit', generateRecommendation);
initializeFarmMap();
window.addEventListener('popstate', renderCurrentPage);

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

for (const button of [primaryAction, primarySecondary]) {
  button.addEventListener('click', () => navigateTo('/register'));
}
for (const button of [loginButton, ctaSecondary]) {
  button.addEventListener('click', () => navigateTo('/login'));
}

document.getElementById('downloadReportButton').addEventListener('click', async () => {
  try {
    const report = await api.get('/api/reports');
    const rows = [['date', 'type', 'details'], ...report.items.map((item) => [new Date(item.createdAt * 1000).toISOString(), item.type, JSON.stringify(item.details)])];
    const csv = rows.map((row) => row.map((field) => `"${String(field).replaceAll('"', '""')}"`).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const downloadLink = document.createElement('a');
    downloadLink.href = url;
    downloadLink.download = 'agriculture-activity-report.csv';
    downloadLink.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    alert(error.message || 'Unable to export activity report.');
  }
});

renderCurrentPage();


// Show a useful explanation when Google redirects back with an authentication error.
const googleAuthErrors = {
  google_not_configured: 'Google sign-in is not configured yet. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to backend/.env, then restart the server.',
  google_state: 'Google sign-in expired or the browser changed host during sign-in. Open http://localhost:8000 and try again.',
  google_exchange: 'Google could not complete sign-in. Check that the OAuth client is a Web application and that its redirect URI exactly matches backend/.env.',
  google_cancelled: 'Google sign-in was cancelled. Select your account and approve the sign-in request to continue.'
};
const googleAuthError = new URLSearchParams(window.location.search).get('auth_error');
if (googleAuthError && googleAuthErrors[googleAuthError]) {
  const message = document.createElement('p');
  message.className = 'map-status';
  message.setAttribute('role', 'alert');
  message.textContent = googleAuthErrors[googleAuthError];
  document.querySelector('.google-auth-content')?.append(message);
}
