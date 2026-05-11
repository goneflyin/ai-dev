INSTALL_DIR = $(HOME)/gbrain

.PHONY: install check test

install:
	@echo "Installing gbrain scripts to $(INSTALL_DIR)/"
	cp sync_matter.py $(INSTALL_DIR)/
	cp todoist_helper.py $(INSTALL_DIR)/
	cp review_matter.py $(INSTALL_DIR)/
	cp status_collect.py $(INSTALL_DIR)/
	@echo "Done."

check:
	python3 -c "import sys; sys.path.insert(0,'.'); import todoist_helper; import review_matter; import status_collect; print('check: all stdlib-only modules import OK')"

test:
	python3 -m pytest tests/ -v
