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
	ctxRequestedConsumerGroups := requestContext.Value("consumerGroup")

	// check if any consumer groups have been set
	var requestedConsumerGroups []string
	if ctxRequestedConsumerGroups == nil {
		vars.HttpLogger.Warn().Msg("no consumer group filter set. prognosis calculation may take more time")
		// since the request did not contain any consumer groups, every consumer group will be used
		consumerGroupRows, queryError := vars.SqlQueries.Query(vars.PostgresConnection, "get-consumer-groups")
		if queryError != nil {
			requestErrors.RespondWithInternalError(queryError, responseWriter)
			return
		}

		// now iterate through the returned rows and collect the consumer groups
		for consumerGroupRows.Next() {
			var consumerGroup string
			scanError := consumerGroupRows.Scan(&consumerGroup)
			if scanError != nil {
				requestErrors.RespondWithInternalError(scanError, responseWriter)
				return
			}
			requestedConsumerGroups = append(requestedConsumerGroups, consumerGroup)
		}

	} else {
		// convert the requested consumer groups into a string array
		requestedConsumerGroups = ctxRequestedConsumerGroups.([]string)
		knownConsumerGroupRows, queryError := vars.SqlQueries.Query(vars.PostgresConnection, "check-consumer-groups",
			pq.Array(requestedConsumerGroups))
		if queryError != nil {
			requestErrors.RespondWithInternalError(queryError, responseWriter)
			return
		}
		// now collect the returned consumer groups
		var knownConsumerGroups []string
		for knownConsumerGroupRows.Next() {
			var consumerGroup string
			scanError := knownConsumerGroupRows.Scan(&consumerGroup)
			if scanError != nil {
				requestErrors.RespondWithInternalError(scanError, responseWriter)
				return
			}

			knownConsumerGroups = append(knownConsumerGroups, consumerGroup)
		}

		// now check if every requested consumer group is found in the database
		for _, requestedConsumerGroup := range requestedConsumerGroups {
			if !utils.ArrayContains(knownConsumerGroups, requestedConsumerGroup) {
				// since the consumer group was not found in the database, the request is rejected
				requestError, err := requestErrors.BuildRequestError(requestErrors.InvalidConsumerGroup)
				if err != nil {
					requestErrors.RespondWithInternalError(err, responseWriter)
					return
				}
				requestErrors.RespondWithRequestError(requestError, responseWriter)
				return
			}
		}
	}

}
