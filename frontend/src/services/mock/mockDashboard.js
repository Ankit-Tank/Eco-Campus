// FAKE DATA. Only used when VITE_USE_MOCK=true. Real numbers must come from the backend.
export const MOCK_PUBLIC_IMPACT = {
  is_simulated: true,
  cards: [
    { key: 'carbon', value: 1240, unit: 'kg', change_pct: 12, equivalent_value: 87 },
    { key: 'electricity', value: 3560, unit: 'kwh', change_pct: 18, equivalent_value: 12 },
    { key: 'water', value: 15200, unit: 'litres', change_pct: 20, equivalent_value: 76 },
    { key: 'waste', value: 320, unit: 'kg', change_pct: 14 },
  ],
}
