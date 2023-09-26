FROM golang:alpine AS build
RUN mkdir -p /build/src
RUN mkdir -p /build/out
COPY src /build/src
WORKDIR /build/src
RUN go mod download
RUN go build -o /build/out/service -x

FROM alpine:latest AS runlevel
COPY --from=build /build/out/service /service
COPY res /res
WORKDIR /
ENTRYPOINT ["/service"]
