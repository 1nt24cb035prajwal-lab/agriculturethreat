DEMO_STATE = {
    "farmer": {
        "id": "F-1001",
        "name": "Ananya Gowda",
        "mobile": "+91 98765 43210",
        "email": "ananya.gowda@example.com",
        "state": "Karnataka",
        "district": "Mysuru",
        "village": "Hunsur",
        "language": "Kannada",
        "password": "demo123",
        "farmName": "Green Valley Farm",
        "farmLocation": "Hunsur, Karnataka",
        "landArea": "12.5 acres",
        "soilType": "Black Soil",
        "irrigationType": "Drip",
        "waterSource": "Borewell",
        "cropName": "Rice",
        "cropVariety": "Jyothi",
        "cropStage": "Flowering",
        "cultivationStart": "2026-06-01",
        "expectedHarvest": "2026-10-15",
        "previousCrop": "Groundnut",
        "farmingMethod": "Conventional"
    },
    "dashboard": {
        "welcome": "Welcome, Ananya",
        "metrics": {
            "totalLand": "12.5 acres",
            "currentCrop": "Rice",
            "growthStage": "Flowering",
            "temperature": "31°C",
            "humidity": "68%",
            "rainfall": "12 mm",
            "soilMoisture": "42%",
            "cropHealth": "Healthy",
            "diseaseRisk": "Medium",
            "waterRequirement": "28 L/day",
            "estimatedYield": "6.2 tons/acre",
            "threatAlerts": 3
        },
        "cards": [
            {"title": "Weather Status", "value": "Partly Cloudy", "detail": "Temperatures around 31°C", "tone": "green"},
            {"title": "Crop Health", "value": "84%", "detail": "Stable vegetative growth", "tone": "blue"},
            {"title": "Disease Risk", "value": "Medium", "detail": "High humidity risk", "tone": "amber"},
            {"title": "Water Requirement", "value": "28 L/day", "detail": "Irrigation scheduled for evening", "tone": "teal"},
            {"title": "Vegetation Health", "value": "NDVI 0.72", "detail": "Healthy canopy cover", "tone": "green"},
            {"title": "Expected Yield", "value": "6.2 t/acre", "detail": "Projected harvest in 18 days", "tone": "purple"},
            {"title": "Fertilizer", "value": "NPK Balanced", "detail": "Apply top dressing in 3 days", "tone": "orange"},
            {"title": "Threat Alerts", "value": "3 Active", "detail": "2 medium, 1 high", "tone": "red"}
        ]
    },
    "weather": {
        "current": {
            "temperature": 31,
            "minTemp": 24,
            "maxTemp": 33,
            "humidity": 68,
            "windSpeed": 14,
            "rainfall": 12,
            "cloudCoverage": 46,
            "summary": "Partly Cloudy"
        },
        "forecast": [
            {"day": "Mon", "temp": 31, "rain": 20, "icon": "☀️"},
            {"day": "Tue", "temp": 30, "rain": 26, "icon": "⛅"},
            {"day": "Wed", "temp": 29, "rain": 42, "icon": "🌧️"},
            {"day": "Thu", "temp": 28, "rain": 18, "icon": "🌦️"},
            {"day": "Fri", "temp": 30, "rain": 10, "icon": "☀️"},
            {"day": "Sat", "temp": 32, "rain": 8, "icon": "☀️"},
            {"day": "Sun", "temp": 31, "rain": 14, "icon": "⛅"}
        ],
        "analysis": [
            "High humidity increases fungal risk in panicle stage.",
            "Light rainfall expected; adjust irrigation frequency.",
            "Warm conditions support crop growth but monitor water stress."
        ]
    },
    "vegetation": {
        "ndvi": 0.72,
        "status": "Healthy vegetation",
        "map": [
            {"zone": "North", "value": 0.81, "label": "Healthy"},
            {"zone": "North-East", "value": 0.69, "label": "Moderate"},
            {"zone": "Center", "value": 0.76, "label": "Healthy"},
            {"zone": "South-West", "value": 0.58, "label": "Stressed"},
            {"zone": "South", "value": 0.64, "label": "Moderate"}
        ],
        "history": [
            {"month": "Jun", "ndvi": 0.55},
            {"month": "Jul", "ndvi": 0.62},
            {"month": "Aug", "ndvi": 0.68},
            {"month": "Sep", "ndvi": 0.72},
            {"month": "Oct", "ndvi": 0.74}
        ]
    },
    "disease": {
        "predictedDisease": "Leaf Blast",
        "confidence": 0.82,
        "severity": "Moderate",
        "symptoms": ["Brown lesions on leaves", "Water-soaked patches", "Reduced vigor"],
        "causes": ["High humidity", "Warm nights", "Dense canopy"],
        "affectedParts": ["Leaves", "Panicles"],
        "preventiveMeasures": ["Avoid excess nitrogen", "Use resistant seed", "Spacing and airflow control"],
        "treatment": "Apply recommended fungicide and reduce water logging.",
        "riskNote": "Further field inspection is recommended before final treatment decisions."
    },
    "water": {
        "dailyRequirement": "28 L/day",
        "weeklyRequirement": "196 L/week",
        "frequency": "Every 2 days",
        "irrigationDuration": "45 minutes",
        "deficiencyRisk": "Low",
        "excessRisk": "Medium",
        "recommendation": "Your crop may require additional irrigation due to high temperatures and low expected rainfall."
    },
    "fertilizer": {
        "recommendations": [
            {"name": "Urea", "purpose": "Nitrogen boost", "quantity": "42 kg/acre", "method": "Top dressing", "timing": "3 days after rain", "precautions": "Apply in split doses"},
            {"name": "DAP", "purpose": "Root establishment", "quantity": "30 kg/acre", "method": "Basal application", "timing": "At planting or transplanting", "precautions": "Keep away from seed contact"},
            {"name": "Potash", "purpose": "Stress resistance", "quantity": "20 kg/acre", "method": "Broadcasting", "timing": "Before panicle initiation", "precautions": "Avoid water-logging after application"}
        ]
    },
    "yield": {
        "expectedYieldPerAcre": "6.2 tons",
        "totalExpectedYield": "77.5 tons",
        "estimatedHarvestDate": "2026-10-15",
        "performance": "Good",
        "yieldReductionRisk": "Low to medium",
        "factors": ["Stable rainfall", "Healthy vegetation index", "Balanced fertilizer plan"]
    },
    "threats": [
        {"name": "Leaf Blast Risk", "risk": "High", "crop": "Rice", "stage": "Flowering", "source": "AI Disease Model", "evidence": "Humidity 68%, NDVI 0.72, observed lesions", "impact": "Can reduce grain quality and total yield.", "preventiveAction": "Improve spacing and spray fungicide", "solution": "Monitor daily and treat at first signs"},
        {"name": "Water Stress", "risk": "Medium", "crop": "Rice", "stage": "Flowering", "source": "Weather + Soil", "evidence": "High temperature and low rain forecast", "impact": "Stunted development and panicle sterility.", "preventiveAction": "Schedule evening irrigation", "solution": "Increase water frequency for 3 days"},
        {"name": "Nutrient Imbalance", "risk": "Low", "crop": "Rice", "stage": "Tillering", "source": "Soil + Fertilizer Analysis", "evidence": "Nitrogen recommendation issued", "impact": "Reduced tiller formation.", "preventiveAction": "Apply split nitrogen dose", "solution": "Check soil sampling report"}
    ],
    "notifications": [
        "High disease risk detected in the rice field.",
        "Irrigation required for the next 2 days.",
        "Vegetation decline is limited; continue monitoring."
    ],
    "reports": {
        "cropHealth": "Stable crop growth with slight disease stress.",
        "diseasePrediction": "Moderate risk of leaf blast confirmed by field and weather data.",
        "weatherAnalysis": "Warm and humid conditions continue for 3 days.",
        "satelliteReport": "NDVI remains above healthy threshold overall.",
        "waterReport": "Water requirement is within expected range for this crop stage.",
        "fertilizerReport": "Balanced NPK, top-dressing recommended after rainfall.",
        "yieldReport": "Projected yield remains strong with manageable seasonal risk.",
        "threatReport": "Priority threats are disease and water stress."
    },
    "admin": {
        "farmers": 248,
        "activeFarms": 196,
        "riskAlerts": 31,
        "weatherStations": 14,
        "diseaseModels": 6,
        "yieldPredictions": 184,
        "reportsGenerated": 126
    }
}
