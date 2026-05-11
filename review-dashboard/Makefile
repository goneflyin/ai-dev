INSTALL_DIR = $(HOME)/gbrain

.PHONY: install check test

install:
	@echo "Installing review dashboard to $(INSTALL_DIR)/"
	cp review_server.py $(INSTALL_DIR)/
	@echo "Done. Start with: python3 $(INSTALL_DIR)/review_server.py --open"

check:
	python3 -W error review_server.py --port 8082 &\
	  SERVER_PID=$$!; sleep 0.3; kill $$SERVER_PID 2>/dev/null; wait $$SERVER_PID 2>/dev/null; \
	  echo "check: no SyntaxWarnings detected"

test:
	python3 -m pytest tests/ -v
