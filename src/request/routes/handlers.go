// Package routes
// This package contains all route handlers for the microservice
package routes

import (
	"github.com/go-chi/chi/v5"
	"github.com/lib/pq"
	"microservice/enums"
	requestErrors "microservice/request/error"
	"microservice/utils"
	"microservice/vars"
	"net/http"
)

// ForecastRequest accepts a new request for a forecast and sends it to the calculation module
func ForecastRequest(responseWriter http.ResponseWriter, request *http.Request) {
	// access the request context object
	requestContext := request.Context()

	// check if the service supports the prognosis mode set in the path
	requestedForecastMethod := enums.ForecastModel(chi.URLParam(request, "forecastMethod"))

	if requestedForecastMethod != enums.LinearForecast &&
		requestedForecastMethod != enums.PolynomialForecast &&
		requestedForecastMethod != enums.LogarithmicForecast {
		// since the method set is not supported, send back an error
		requestError, err := requestErrors.BuildRequestError(requestErrors.UnsupportedForecastMethod)
		if err != nil {
			requestErrors.RespondWithInternalError(err, responseWriter)
			return
		}
		requestErrors.RespondWithRequestError(requestError, responseWriter)
		return
	}

	// now access the context of the request and get the municipality keys set in the query url
	ctxRequestedMunicipalityKeys := requestContext.Value("key")

	// now check if the keys are even set
	if ctxRequestedMunicipalityKeys == nil {
		// since the request did not contain any municipality keys, send back an error
		requestError, err := requestErrors.BuildRequestError(requestErrors.MissingShapeKeys)
		if err != nil {
			requestErrors.RespondWithInternalError(err, responseWriter)
			return
		}
		requestErrors.RespondWithRequestError(requestError, responseWriter)
		return
	}

	// since some municipality keys have been set convert the requested keys into an array
	requestedMunicipalityKeys := ctxRequestedMunicipalityKeys.([]string)

	// now check if the municipality keys exist
	knownMunicipalityKeyRows, queryError := vars.SqlQueries.Query(vars.PostgresConnection, "check-municipality-keys",
		pq.Array(requestedMunicipalityKeys))
	if queryError != nil {
		requestErrors.RespondWithInternalError(queryError, responseWriter)
		return
	}

	// now iterate through the returned rows and collect the known municipality keys
	var knownMunicipalityKeys []string
	for knownMunicipalityKeyRows.Next() {
		var knownMunicipalityKey string

		err := knownMunicipalityKeyRows.Scan(&knownMunicipalityKey)
		if err != nil {
			requestErrors.RespondWithInternalError(queryError, responseWriter)
			return
		}

		knownMunicipalityKeys = append(knownMunicipalityKeys, knownMunicipalityKey)
	}

	// now check if every requested municipality key is in the just collected known municipality keys
	for _, requestedMunicipalityKey := range requestedMunicipalityKeys {
		if !utils.ArrayContains(knownMunicipalityKeys, requestedMunicipalityKey) {
			// since the key was not found in the database, the request is rejected
			requestError, err := requestErrors.BuildRequestError(requestErrors.InvalidShapeKey)
			if err != nil {
				requestErrors.RespondWithInternalError(err, responseWriter)
				return
			}
			requestErrors.RespondWithRequestError(requestError, responseWriter)
			return
		}
	}

	// since all municipality keys passed the check, the consumer groups will now be checked if they are supplied
}
