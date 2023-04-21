package structs

import (
	amqp "github.com/rabbitmq/amqp091-go"
	"microservice/enums"
)

// This file contains the structs that are used to communicate with the
// AMQP message broker and the calculation module.

type AMQP struct {
	Connection    *amqp.Connection
	Channel       *amqp.Channel
	CallbackQueue amqp.Queue
}

type CalculationRequest struct {
	Model           enums.ForecastModel `json:"model"`
	Keys            []string            `json:"keys"`
	ConsumerGroups  []string            `json:"consumerGroups"`
	ForecastedYears int                 `json:"forecastSize"`
}
