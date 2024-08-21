FROM golang:1.22-alpine3.20 AS build

RUN go install github.com/piunov1998/SpoofDPI/cmd/spoof-dpi@latest

FROM scratch
COPY --from=build /go/bin/spoof-dpi /opt/spoof-dpi

WORKDIR /opt
CMD ["./spoof-dpi", "-addr", "0.0.0.0", "-no-banner"]
