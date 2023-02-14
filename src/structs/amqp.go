package structs

import "microservice/enums"

type AMQPForecastRequest struct {
	Model          enums.ForecastModel `json:"model"`
	MunicipalKeys  []string            `json:"keys"`
	ConsumerGroups []string            `json:"consumerGroups"`
	ForecastYears  int                 `json:"forecastSize"`
}
