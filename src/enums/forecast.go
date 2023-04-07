package enums

type ForecastModel string

const (
	LINEAR      ForecastModel = "linear"
	EXPONENTIAL ForecastModel = "exponential"
	POLYNOMIAL  ForecastModel = "polynomial"
)
