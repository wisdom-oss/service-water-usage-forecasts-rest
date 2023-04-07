package structs

import "microservice/enums"

// This file contains the structs that are used to communicate with the
// AMQP message broker and the calculation module.

type CalculationRequest struct {
	Model           enums.ForecastModel `json:"model"`
	Keys            []string            `json:"keys"`
	ConsumerGroups  []string            `json:"consumerGroups"`
	ForecastedYears int                 `json:"forecastSize"`
}
