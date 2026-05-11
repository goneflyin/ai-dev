SKILLS_DIR = $(HOME)/.hermes/skills

.PHONY: install check

install:
	@echo "Installing skills to $(SKILLS_DIR)/"
	@for dir in */; do \
		if [ -f "$${dir}SKILL.md" ]; then \
			mkdir -p $(SKILLS_DIR)/$${dir}; \
			cp $${dir}SKILL.md $(SKILLS_DIR)/$${dir}/; \
			echo "  Installed $${dir}SKILL.md"; \
		fi; \
	done
	@echo "Done."

check:
	@for dir in */; do \
		if [ -f "$${dir}SKILL.md" ]; then \
			echo "  ✓ $${dir}"; \
		fi; \
	done