/**
 * Type definitions for Octopus Energy España consumption card.
 */

export interface OctopusConsumptionCardConfig {
  type: "custom:octopus-consumption-card";
  entity: string;
  title?: string;
  show_comparison?: boolean;
  default_period?: "day" | "week" | "month";
  chart_type?: "line" | "bar";
  // Tariff comparison options
  show_tariff_comparison?: boolean;
  tariff_entry_ids?: string[];
  show_cost_on_chart?: boolean;
  selected_tariff_for_cost?: string;
  // Period navigation
  show_navigation?: boolean;
}

export interface ConsumptionDataPoint {
  start_time: string;
  consumption: number;
  value?: number;
  date?: string;
}

export interface PriceDataPoint {
  start_time: string;
  price_per_kwh: number;
}

export interface TariffCostBreakdown {
  total_cost: number;
  energy_cost: number;
  power_cost: number;
  management_fee: number;
  taxes: number;
  hourly_breakdown: Array<{
    hour: string;
    cost: number;
    consumption: number;
    period: string | null;
  }>;
  daily_breakdown: Array<{
    date: string;
    cost: number;
    consumption: number;
  }>;
  period_breakdown: {
    p1_consumption: number;
    p2_consumption: number;
    p3_consumption: number;
    p1_percentage: number;
    p2_percentage: number;
    p3_percentage: number;
    total_consumption: number;
  };
}

export interface TariffComparisonResult {
  entry_id: string;
  name: string;
  total_cost: number;
  energy_cost: number;
  power_cost: number;
  management_fee: number;
  taxes: number;
  hourly_breakdown: TariffCostBreakdown["hourly_breakdown"];
  daily_breakdown: TariffCostBreakdown["daily_breakdown"];
  period_breakdown: TariffCostBreakdown["period_breakdown"];
}

export interface ComparisonResult {
  period: string;
  consumption_total: number;
  tariffs: TariffComparisonResult[];
  best_tariff: {
    entry_id: string;
    name: string;
    total_cost: number;
  } | null;
  savings: {
    best_entry_id: string;
    worst_entry_id: string;
    amount: number;
    percentage: number;
  } | null;
  start_date?: string | null;
  end_date?: string | null;
  error?: string;
  warning?: string;
  invalid_entry_ids?: string[];
}

export interface FetchConsumptionResult {
  success: boolean;
  consumption_data?: ConsumptionDataPoint[];
  tariff_costs?: Record<string, TariffCostBreakdown>;
  error?: string;
  warning?: string;
}
