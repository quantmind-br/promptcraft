PACKAGE_NAME = promptcraft
BIN_DIR ?= $(HOME)/.local/bin
GO_TARGET = ./cmd/promptcraft

.PHONY: install uninstall reinstall build test lint

# Install (or update) the Go binary on the PATH. go build overwrites an existing
# copy, so running make install again is just an update.
install:
	@mkdir -p $(BIN_DIR)
	go build -o $(BIN_DIR)/$(PACKAGE_NAME) $(GO_TARGET)
	@echo "installed: $(BIN_DIR)/$(PACKAGE_NAME)"
	@case ":$(PATH):" in *":$(BIN_DIR):"*) ;; *) echo "warning: $(BIN_DIR) is not on PATH" ;; esac

uninstall:
	@rm -f $(BIN_DIR)/$(PACKAGE_NAME)
	@echo "removed: $(BIN_DIR)/$(PACKAGE_NAME)"

reinstall: install

build:
	go build -o $(PACKAGE_NAME) $(GO_TARGET)

test:
	go test -race ./...

lint:
	golangci-lint run ./...
