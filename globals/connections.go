package globals

import (
	"database/sql"
	"microservice/wrapper"
)

// This file contains all globally shared connections (e.g., Databases)

// Db contains the globally available connection to the database
var Db *sql.DB

// Amqp contains the connection and channel used to communicate with the message
// broker used to send the forecast requests
var Amqp wrapper.AMQP
