package wisdomMiddleware

import (
	"github.com/rs/zerolog/log"
	"github.com/wisdom-oss/microservice-utils"
	"net/http"
	"strings"
)

func Authorization(excludedPaths []string, requiredGroup string) func(http.Handler) http.Handler {
	logger := log.With().Str("wisdomMiddleware", "Authorization").Logger()
	return func(nextHandler http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			logger.Info().Msg("checking authorization for request")
			// check if the request path is listed in the excluded paths
			requestPath := r.URL.Path
			if wisdomUtils.ArrayContains(excludedPaths, requestPath) {
				log.Info().Str("path", requestPath).Msg("skipping authorization check for excluded path")
				nextHandler.ServeHTTP(w, r)
				return
			}

			// now get the groups and the username which were set as a header
			groupString := r.Header.Get("X-Authenticated-Groups")
			username := r.Header.Get("X-Authenticated-User")

			// now check if any groups were set
			if strings.TrimSpace(groupString) == "" {
				logger.Warn().Str("reason", "groups-missing").Msg("unauthorized request blocked")
				w.WriteHeader(401)
				return
			}

			// now check if the username was set
			if strings.TrimSpace(username) == "" {
				logger.Warn().Str("reason", "username-missing").Msg("unauthorized request blocked")
				w.WriteHeader(401)
			}

			// now make an array from the groups that were set in the header
			groups := strings.Split(groupString, ",")
			if !wisdomUtils.ArrayContains(groups, requiredGroup) {
				logger.Warn().Str("reason", "group-incorrect").Msg("forbidden request blocked")
				w.WriteHeader(403)
				return
			}

			// since the request seems to be authorized call the next handler
			nextHandler.ServeHTTP(w, r)

		})
	}
}
