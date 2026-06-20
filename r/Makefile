.PHONY: setup test report clean

setup:
	Rscript -e "renv::restore(prompt = FALSE)"
	Rscript -e "pkgs <- c('optparse', 'quarto', 'devtools', 'roxygen2', 'withr', 'testthat'); \
		missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]; \
		if (length(missing)) renv::install(missing, prompt = FALSE)"

test:
	Rscript -e "devtools::test('.')"

report:
	Rscript scripts/run.R

clean:
	rm -rf reports/*/
