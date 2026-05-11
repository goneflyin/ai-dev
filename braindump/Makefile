INSTALL_DIR = $(HOME)/gbrain

.PHONY: install check test

install:
	@echo "Installing braindump scripts to $(INSTALL_DIR)/"
	cp braindump.py $(INSTALL_DIR)/
	cp braindump_watchdog.py $(INSTALL_DIR)/
	@echo "Done."

check:
	python3 -c "import sys; sys.path.insert(0,'.'); from braindump import last_braindump_age_hours, nudge_message, write_braindump; print('check: braindump imports OK')"

test:
	python3 -m pytest tests/ -v
