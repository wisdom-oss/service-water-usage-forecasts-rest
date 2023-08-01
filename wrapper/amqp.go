package wrapper

import amqp "github.com/rabbitmq/amqp091-go"

type AMQP struct {
	Connection *amqp.Connection
	Channel    *amqp.Channel
}
