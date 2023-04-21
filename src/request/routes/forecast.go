package routes

import (
	"encoding/json"
	"github.com/go-chi/chi/v5"
	"github.com/lib/pq"
	"microservice/enums"
	requestErrors "microservice/request/error"
	"microservice/structs"
	"microservice/vars/globals"
	"microservice/vars/globals/connections"
	"net/http"
)

// l is an alias for shorter code
var l = globals.HttpLogger

func NewForecast(w http.ResponseWriter, r *http.Request) {
	l.Info().Msg("new forecast requested")

	// get the model from the url
	m := chi.URLParam(r, "model")
	model := enums.ForecastModel(m)
	if model != enums.LINEAR_FORECAST && model != enums.EXPONENTIAL_FORECAST && model != enums.POLYNOMIAL_FORECAST {
		l.Warn().Msg("invalid model requested. rejecting request")
		e, err := requestErrors.GetRequestError("INVALID_FORECAST_MODEL")
		if err != nil {
			l.Error().Err(err).Msg("an error occurred while getting the request error")
			e, _ = requestErrors.WrapInternalError(err)
		}
		requestErrors.SendError(e, w)
		return
	}

	// now check if the query parameters contain area keys
	areaKeys, areaKeysSet := r.URL.Query()["key"]
	if !areaKeysSet {
		l.Warn().Msg("no area keys provided. rejecting request")
		e, err := requestErrors.GetRequestError("NO_AREA_KEYS")
		if err != nil {
			l.Error().Err(err).Msg("an error occurred while getting the request error")
			e, _ = requestErrors.WrapInternalError(err)
		}
		requestErrors.SendError(e, w)
		return
	}

	// since the area keys are now integers the database search will be faster
	knownAreaKeyRows, queryError := globals.Queries.Query(connections.DbConnection, "check-area-keys", pq.Array(areaKeys))
	if queryError != nil {
		l.Error().Err(queryError).Msg("an error occurred while querying the database")
		e, err := requestErrors.WrapInternalError(queryError)
		if err != nil {
			l.Error().Err(err).Msg("an error occurred while getting the request error")
			e, _ = requestErrors.WrapInternalError(err)
		}
		requestErrors.SendError(e, w)
		return
	}

	var knownAreaKeys []string
	for knownAreaKeyRows.Next() {
		var knownAreaKey string
		scanError := knownAreaKeyRows.Scan(&knownAreaKey)
		if scanError != nil {
			l.Error().Err(scanError).Msg("an error occurred while scanning the database result")
			e, err := requestErrors.WrapInternalError(scanError)
			if err != nil {
				l.Error().Err(err).Msg("an error occurred while getting the request error")
				e, _ = requestErrors.WrapInternalError(err)
			}
			requestErrors.SendError(e, w)
			return
		}
		knownAreaKeys = append(knownAreaKeys, knownAreaKey)
	}

	if len(knownAreaKeys) < len(areaKeys) {
		l.Warn().Msg("some area keys are unknown. rejecting request")
		e, err := requestErrors.GetRequestError("INVALID_AREA_KEYS")
		if err != nil {
			l.Error().Err(err).Msg("an error occurred while getting the request error")
			e, _ = requestErrors.WrapInternalError(err)
		}
		requestErrors.SendError(e, w)
		return
	}

	// now validate the consumer groups
	consumerGroups, consumerGroupsSet := r.URL.Query()["consumerGroup"]
	if !consumerGroupsSet {
		l.Info().Msg("no consumer groups provided. using all consumer groups")
		consumerGroupRows, queryError := globals.Queries.Query(connections.DbConnection, "get-all-consumer-groups")
		if queryError != nil {
			l.Error().Err(queryError).Msg("an error occurred while querying the database")
			e, err := requestErrors.WrapInternalError(queryError)
			if err != nil {
				l.Error().Err(err).Msg("an error occurred while getting the request error")
				e, _ = requestErrors.WrapInternalError(err)
			}
			requestErrors.SendError(e, w)
			return
		}
		for consumerGroupRows.Next() {
			var consumerGroup string
			scanError := consumerGroupRows.Scan(&consumerGroup)
			if scanError != nil {
				l.Error().Err(scanError).Msg("an error occurred while scanning the database result")
				e, err := requestErrors.WrapInternalError(scanError)
				if err != nil {
					l.Error().Err(err).Msg("an error occurred while getting the request error")
					e, _ = requestErrors.WrapInternalError(err)
				}
				requestErrors.SendError(e, w)
				return
			}
			consumerGroups = append(consumerGroups, consumerGroup)
		}
	} else {
		knownConsumerGroupRows, queryError := globals.Queries.Query(connections.DbConnection, "check-consumer-groups", pq.Array(consumerGroups))
		if queryError != nil {
			l.Error().Err(queryError).Msg("an error occurred while querying the database")
			e, err := requestErrors.WrapInternalError(queryError)
			if err != nil {
				l.Error().Err(err).Msg("an error occurred while getting the request error")
				e, _ = requestErrors.WrapInternalError(err)
			}
			requestErrors.SendError(e, w)
			return
		}

		var knownConsumerGroups []string
		for knownConsumerGroupRows.Next() {
			var knownConsumerGroup string
			scanError := knownConsumerGroupRows.Scan(&knownConsumerGroup)
			if scanError != nil {
				l.Error().Err(scanError).Msg("an error occurred while scanning the database result")
				e, err := requestErrors.WrapInternalError(scanError)
				if err != nil {
					l.Error().Err(err).Msg("an error occurred while getting the request error")
					e, _ = requestErrors.WrapInternalError(err)
				}
				requestErrors.SendError(e, w)
				return
			}
			knownConsumerGroups = append(knownConsumerGroups, knownConsumerGroup)
		}

		if len(knownConsumerGroups) < len(consumerGroups) {
			l.Warn().Msg("some consumer groups are unknown. rejecting request")
			e, err := requestErrors.GetRequestError("INVALID_CONSUMER_GROUPS")
			if err != nil {
				l.Error().Err(err).Msg("an error occurred while getting the request error")
				e, _ = requestErrors.WrapInternalError(err)
			}
			requestErrors.SendError(e, w)
			return
		}
	}

	// since the possible data now is validated create the request
	forecastRequest := structs.CalculationRequest{
		Model:           model,
		Keys:            areaKeys,
		ConsumerGroups:  consumerGroups,
		ForecastedYears: 20,
	}

	// now convert that into a string
	message, marshalError := json.Marshal(forecastRequest)
	if marshalError != nil {
		l.Error().Err(marshalError).Msg("unable to convert forecast request into message body")
		e, _ := requestErrors.WrapInternalError(marshalError)
		requestErrors.SendError(e, w)
		return
	}

}
