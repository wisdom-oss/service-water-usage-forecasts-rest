package types

import "microservice/enums"

type CalculationRequest struct {
	Model           enums.ForecastModel `json:"model"`
	Keys            []string            `json:"keys"`
	ConsumerGroups  []string            `json:"consumerGroups"`
	ForecastedYears int                 `json:"forecastSize"`
}
