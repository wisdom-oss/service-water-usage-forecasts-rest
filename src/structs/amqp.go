package structs

type AMQPForecastRequest struct {
	Model          ForecastModel `json:"model"`
	MunicipalKeys  []string      `json:"keys"`
	ConsumerGroups []string      `json:"consumerGroups"`
	ForecastYears  int           `json:"forecastSize"`
}
