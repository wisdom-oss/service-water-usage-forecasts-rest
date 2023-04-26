package enums

type ForecastModel string

const (
	LINEAR_FORECAST      ForecastModel = "linear"
	EXPONENTIAL_FORECAST ForecastModel = "exponential"
	POLYNOMIAL_FORECAST  ForecastModel = "polynomial"
)
