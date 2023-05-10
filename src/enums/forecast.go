package enums

type ForecastModel string

const (
	LINEAR_FORECAST      ForecastModel = "linear"
	LOGARITHMIC_FORECAST ForecastModel = "logarithmic"
	POLYNOMIAL_FORECAST  ForecastModel = "polynomial"
)
