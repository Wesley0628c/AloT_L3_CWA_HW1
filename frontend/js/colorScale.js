/**
 * Returns hex color string for a given temperature value (°C)
 * Legend ranges:
 *  < 10°C: #2b6cb0 (Cold / 嚴寒)
 *  10-15°C: #3182ce (Cool / 寒冷)
 *  15-20°C: #38a169 (Mild / 涼爽)
 *  20-25°C: #ecc94b (Comfortable / 舒適)
 *  25-30°C: #ed8936 (Warm / 溫暖)
 *  30-35°C: #e53e3e (Hot / 炎熱)
 *  > 35°C: #9b2c2c (Very Hot / 酷熱)
 */
function colorByTemperature(temp) {
    if (temp === null || temp === undefined || isNaN(temp)) return "#94a3b8";
    if (temp < 10) return "#2b6cb0";
    if (temp < 15) return "#3182ce";
    if (temp < 20) return "#38a169";
    if (temp < 25) return "#ecc94b";
    if (temp < 30) return "#ed8936";
    if (temp < 35) return "#e53e3e";
    return "#9b2c2c";
}

/**
 * Returns circle marker radius based on temperature
 */
function getMarkerRadius(temp) {
    if (temp < 15) return 7;
    if (temp < 25) return 8;
    if (temp < 30) return 9;
    return 10;
}
