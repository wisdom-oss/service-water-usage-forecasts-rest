package routes

import (
	"context"
	"encoding/json"
	"github.com/go-chi/chi/v5"
	chiMiddleware "github.com/go-chi/chi/v5/middleware"
	"github.com/lib/pq"
	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/rs/zerolog/log"
	"microservice/enums"
	"microservice/globals"
	"microservice/types"
	"net/http"
	"time"
)

func NewForecast(w http.ResponseWriter, r *http.Request) {
	// get the error handlers from the request context
	nativeErrorChannel := r.Context().Value("nativeErrorChannel").(chan error)
	nativeErrorHandled := r.Context().Value("nativeErrorHandled").(chan bool)
	wisdomErrorChannel := r.Context().Value("wisdomErrorChannel").(chan string)
	wisdomErrorHandled := r.Context().Value("wisdomErrorHandled").(chan bool)

	// resolve the wanted model from the url and make it into a forecast model
	model := enums.ForecastModel(chi.URLParam(r, "model"))

	// now check if the model if one of the supported ones
	if model != enums.LINEAR &&
		model != enums.LOGARITHMIC &&
		model != enums.POLYNOMIAL {
		wisdomErrorChannel <- "INVALID_FORECAST_MODEL"
		<-wisdomErrorHandled
		return
	}

	// now get the municipal/area keys from the query parameters
	keys, keysSet := r.URL.Query()["key"]
	if !keysSet {
		wisdomErrorChannel <- "NO_AREA_KEYS"
		<-wisdomErrorHandled
		return
	}

	// now query the database to count the keys available in the database
	// matching those contained in the set of keys set in the query
	keyCountRow, err := globals.SqlQueries.QueryRow(globals.Db, "count-keys", pq.Array(keys))
	if err != nil {
		nativeErrorChannel <- err
		<-nativeErrorHandled
		return
	}
	var keyCount int
	err = keyCountRow.Scan(&keyCount)
	if err != nil {
		nativeErrorChannel <- err
		<-nativeErrorHandled
		return
	}
	// now check if the key count from the database matches the count of keys
	// set in the query
	if len(keys) != keyCount {
		wisdomErrorChannel <- "INVALID_AREA_KEYS"
		<-wisdomErrorHandled
		return
	}

	// now get the consumer groups from the query parameters
	cGroups, cGroupsSet := r.URL.Query()["consumerGroup"]
	if cGroupsSet {
		// if consumer groups are set, validate them
		cGroupCountRow, err := globals.SqlQueries.QueryRow(globals.Db, "count-consumer-groups", pq.Array(cGroups))
		if err != nil {
			nativeErrorChannel <- err
			<-nativeErrorHandled
			return
		}
		var cGroupCount int
		err = cGroupCountRow.Scan(&cGroupCount)
		if err != nil {
			nativeErrorChannel <- err
			<-nativeErrorHandled
			return
		}

		// now check that the length matches the number of consumer groups
		// provided in the query
		if len(cGroups) != cGroupCount {
			wisdomErrorChannel <- "INVALID_CONSUMER_GROUPS"
			<-wisdomErrorHandled
			return
		}
	}

	// now build the request and convert it into bytes
	forecastRequest := types.CalculationRequest{
		Model:           model,
		Keys:            keys,
		ConsumerGroups:  cGroups,
		ForecastedYears: 20,
	}
	messageContent, err := json.Marshal(forecastRequest)
	if err != nil {
		nativeErrorChannel <- err
		<-nativeErrorHandled
		return
	}

	// get the request id generated for this request
	requestIdentification := chiMiddleware.GetReqID(r.Context())

	// now using the amqp channel that is globally available, open up a
	// response queue for this request
	responseQueue, err := globals.Amqp.Channel.QueueDeclare(
		requestIdentification,
		false,
		true,
		true,
		false,
		nil,
	)
	log.Debug().Str("queueName", responseQueue.Name).Msg("opened new response queue")

	// and start listening on the just created queue
	responses, err := globals.Amqp.Channel.Consume(
		responseQueue.Name,
		requestIdentification,
		true,
		false,
		false,
		false,
		nil,
	)

	// now create a new context with a timeout of 5 minutes
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Minute)
	defer cancel()

	// now publish the message
	err = globals.Amqp.Channel.PublishWithContext(ctx,
		globals.Environment["AMQP_EXCHANGE"],
		globals.Environment["CALCULATION_MODULE_ROUTING_KEY"],
		false,
		false,
		amqp.Publishing{
			ContentType:     "application/json",
			ContentEncoding: "utf-8",
			CorrelationId:   requestIdentification,
			ReplyTo:         responseQueue.Name,
			Body:            messageContent,
		},
	)
	if err != nil {
		nativeErrorChannel <- err
		<-nativeErrorHandled
		return
	}
	// now check the incoming responses and validate the correlation id on them
responseLoop:
	for {
		select {
		case <-ctx.Done():
			log.Error().Msg("calculation module timeout")
			wisdomErrorChannel <- "CALCULATION_MODULE_SLOW"
			<-wisdomErrorHandled
			break responseLoop
		case response := <-responses:
			// check the response correlation ids
			if response.CorrelationId != requestIdentification {
				// since no correlation id was found, just run the next
				// iteration
				log.Debug().Msg("response does not request id")
				continue
			}
			// since the correlation ids match, return the response
			w.Header().Set("Content-Type", "text/json")
			_, err = w.Write(response.Body)
			if err != nil {
				nativeErrorChannel <- err
				<-nativeErrorHandled
				break responseLoop
			}
			break responseLoop
		}
	}
	// now clean up the opened connections, listeners, etc.
	err = globals.Amqp.Channel.Cancel(requestIdentification, false)
	if err != nil {
		log.Error().Err(err).Msg("unable to stop consuming response queue")
	}
	_, err = globals.Amqp.Channel.QueueDelete(responseQueue.Name,
		false, false, false)
	if err != nil {
		log.Error().Err(err).Msg("unable to delete the response queue")
	}
}
