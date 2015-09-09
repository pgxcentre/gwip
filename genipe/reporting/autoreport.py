
# This file is part of genipe.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.


import os
import shutil
from datetime import date

from pkg_resources import resource_filename

from .utils import *
from .. import __version__
from .. import chromosomes
from ..error import ProgramError


__author__ = "Louis-Philippe Lemieux Perreault"
__copyright__ = "Copyright 2014, Beaulieu-Saucier Pharmacogenomics Centre"
__license__ = "Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)"


__all__ = ["generate_report", ]


def generate_report(out_dir, run_opts, run_info):
    """Generate the report.

    Args:
        out_dir (str): the output directory for the report
        run_opts (dict): the run options
        run_info (dict): the run information

    """
    # Configuring Jinja2
    jinja2_env = config_jinja2()

    # Gathering the report data
    today = date.today()
    report_data = {
        "report_number":   sanitize_tex(run_opts.report_number),
        "title":           sanitize_tex(run_opts.report_title),
        "author":          sanitize_tex(run_opts.report_author),
        "month":           sanitize_tex("{:%B}".format(today)),
        "day":             sanitize_tex("{:%d}".format(today)),
        "year":            sanitize_tex("{:%Y}".format(today)),
        "package_name":    sanitize_tex(__name__.split(".")[0]),
        "package_version": sanitize_tex(__version__),
    }

    # We want to copy the figures to the right place
    figures = ["frequency_pie"]
    for figure in figures:
        assert figure in run_info, figure
        if run_info[figure] != "":
            shutil.copy(run_info[figure], out_dir)
            run_info[figure] = os.path.basename(run_info[figure])

    # Gathering the report content
    report_content = ""
    report_content += _generate_background(jinja2_env, run_opts, run_info)
    report_content += _generate_methods(jinja2_env, run_opts, run_info)
    report_content += _generate_results(jinja2_env, run_opts, run_info)
    report_content += _generate_conclusions(jinja2_env, run_opts, run_info)
    report_data["report_content"] = report_content

    # Gathering the annex content
    annex_content = _generate_annex(jinja2_env, run_opts, run_info)
    report_data["annex_content"] = annex_content

    # Getting the template
    main_template = jinja2_env.get_template("main_template.tex")

    # Writing the report
    report_filename = os.path.join(out_dir, "report.tex")
    try:
        with open(report_filename, "w") as o_file:
            print(main_template.render(**report_data), file=o_file)

    except FileNotFoundError:
        raise ProgramError("{}: cannot write file".format(report_filename))

    # Copying the bibliography file
    bib_file = resource_filename(__name__, "templates/biblio/references.bib")
    shutil.copy(bib_file, out_dir)

    # Copying the bibliography style
    bib_style = resource_filename(__name__, "templates/biblio/references.bst")
    shutil.copy(bib_style, out_dir)

    # Copying the Makefile (to help build the report)
    makefile = resource_filename(__name__, "templates/utils/Makefile")
    shutil.copy(makefile, out_dir)


def _generate_background(templates, run_options, run_information):
    """Generates the background section of the report.

    Args:
        templates (jinja2.Environment): the jinja2 template environment
        run_options (dict): the run options
        run_information (dict): the run information

    Returns:
        str: a string representation of the "background" section

    """
    # Loading the template
    section_template = templates.get_template("section_template.tex")
    background = templates.get_template("parts/background.tex")

    # Returning the section
    return section_template.render(
        section_name="Background",
        section_type="section",
        section_label="sec:background",
        section_content=background.render(**run_information),
    )


def _generate_methods(templates, run_options, run_information):
    """Generate the method section of the report.

    Args:
        templates (jinja2.Environment): the jinja2 template environment
        run_options (dict): the run options
        run_information (dict): the run information

    Returns:
        str: a string representation of the "methods" section

    """
    # Some assertions
    required_variables = ["shapeit_version", "impute2_version",
                          "plink_version", "initial_nb_markers",
                          "initial_nb_samples", "nb_duplicates",
                          "nb_ambiguous", "nb_flip", "nb_exclude",
                          "nb_phasing_markers", "nb_flip_reference",
                          "reference_checked"]
    for required_variable in required_variables:
        assert required_variable in run_information, required_variable

    # Loading the templates
    section_template = templates.get_template("section_template.tex")
    itemize_template = templates.get_template("iterate_template.tex")
    methods = templates.get_template("parts/methods.tex")

    # Are there any filtering rules?
    filtering_rules = ""
    if run_options.filtering_rules is not None:
        filtering_rules = sanitize_tex(" (filtering out sites where")
        for i, rule in enumerate(run_options.filtering_rules):
            p = ", "
            if i == 0:
                p = " "
            elif i == len(run_options.filtering_rules) - 1:
                p = " or "
            p = sanitize_tex(p)
            filtering_rules += p + format_tex(sanitize_tex(rule), "texttt")
        filtering_rules += sanitize_tex(")")

    # The input files
    data_files = [
        "{}.{}".format(run_options.bfile, ext) for ext in ("bed", "bim", "fam")
    ]

    # The text for the different steps
    steps = []

    # Was there an initial reference check?
    to_add_1 = ""
    to_add_2 = ""
    if run_information["reference_checked"]:
        to_add_1 = sanitize_tex(
            "An initial strand check was also performed using the human "
            "reference genome. "
        )
        to_add_2 = format_tex(
            sanitize_tex(
                " Also, {nb_flip} markers were flipped because of strand "
                "issue.".format(
                    nb_flip=run_information["nb_flip_reference"],
                )
            ),
            "textbf",
        )

    # The ambiguous and duplicated markers that were removed
    steps.append(wrap_tex(sanitize_tex(
        "Ambiguous markers with alleles "
    ) + format_tex("A", "texttt") + "/" + format_tex("T", "texttt") + " and " +
        format_tex("C", "texttt") + "/" + format_tex("G", "texttt") +
        sanitize_tex(
            ", duplicated markers (same position), and markers located on "
            "sexual or mitochondrial chromosomes were excluded from the "
            "imputation. "
    ) + to_add_1 + format_tex(
        sanitize_tex(
            "In total, {ambiguous} ambiguous, {duplicated} duplicated and "
            "{special} non-autosomal markers were excluded.".format(
                ambiguous=run_information["nb_ambiguous"],
                duplicated=run_information["nb_duplicates"],
                special=run_information["nb_special_markers"],
            )
        ),
        "textbf",
    ) + to_add_2))

    # The number of markers that were flipped
    steps.append(wrap_tex(sanitize_tex(
        "Markers' strand was checked using the SHAPEIT algorithm and "
        "IMPUTE2's reference files. "
    ) + format_tex(
        sanitize_tex(
            "In total, {nb_markers} markers had an incorrect strand and "
            "were flipped using Plink.".format(
                nb_markers=run_information["nb_flip"],
            )
        ),
        "textbf",
    )))

    # The number of excluded markers because of strand problem
    steps.append(wrap_tex(sanitize_tex(
        "The strand of each marker was checked again using SHAPEIT against "
        "IMPUTE2's reference files. "
    ) + format_tex(
        sanitize_tex(
            "In total, {nb_markers} markers were found to still be on the "
            "wrong strand, and were hence excluded from the final dataset "
            "using Plink.".format(
                nb_markers=run_information["nb_exclude"],
            )
        ),
        "textbf",
    )))

    steps = itemize_template.render(iteration_type="enumerate",
                                    iteration_list=steps)

    # Returning the section
    return section_template.render(
        section_name="Methods",
        section_type="section",
        section_label="sec:methods",
        section_content=methods.render(
            data_files=data_files,
            steps_data=steps,
            filtering_rules=filtering_rules,
            **run_information
        ),
    )


def _generate_results(templates, run_options, run_information):
    """Generates the results section of the report.

    Args:
        templates (jinja2.Environment): the jinja2 template environment
        run_options (dict): the run options
        run_information (dict): the run information

    Returns:
        str: a string representation of the "results" section

    """
    # Some assertions
    required_variables = ["cross_validation_final_nb_genotypes",
                          "cross_validation_nb_genotypes_chrom",
                          "cross_validation_table_1",
                          "cross_validation_table_2",
                          "cross_validation_table_1_chrom",
                          "cross_validation_table_2_chrom", "prob_threshold",
                          "nb_imputed", "average_comp_rate", "rate_threshold",
                          "info_threshold", "nb_good_sites",
                          "average_comp_rate_cleaned", "mean_missing",
                          "nb_samples", "nb_genotyped",
                          "nb_genotyped_not_complete",
                          "pct_genotyped_not_complete", "nb_geno_now_complete",
                          "pct_geno_now_complete", "nb_site_now_complete",
                          "pct_good_sites", "nb_missing_geno", "nb_maf_nan",
                          "nb_marker_with_maf", "nb_maf_geq_01",
                          "nb_maf_geq_05", "nb_maf_lt_05", "nb_maf_lt_01",
                          "nb_maf_geq_01_lt_05", "pct_maf_geq_01",
                          "pct_maf_geq_05", "pct_maf_lt_05", "pct_maf_lt_01",
                          "pct_maf_geq_01_lt_05", "frequency_pie"]

    for required_variable in required_variables:
        assert required_variable in run_information, required_variable

    # Loading the templates
    section_template = templates.get_template("section_template.tex")
    tabular_template = templates.get_template("tabular_template.tex")
    graphics_template = templates.get_template("graphics_template.tex")
    float_template = templates.get_template("float_template.tex")
    cross_validation = templates.get_template("parts/cross_validation.tex")
    completion_rate = templates.get_template("parts/completion_rate.tex")
    frequencies = templates.get_template("parts/frequencies.tex")

    # The header of the two kind of tables
    header_table_1 = [
        format_tex(sanitize_tex("Interval"), "textbf"),
        format_tex(sanitize_tex("Nb Geno"), "textbf"),
        format_tex(sanitize_tex("Concordance (%)"), "textbf"),
    ]
    header_table_2 = [
        format_tex(sanitize_tex("Interval"), "textbf"),
        format_tex(sanitize_tex("Called (%)"), "textbf"),
        format_tex(sanitize_tex("Concordance (%)"), "textbf"),
    ]

    # Creating the tables
    tables = ""

    # Adding the table for each of the chromosomes
    for chrom in chromosomes:
        # Getting the table 1
        table_1 = run_information["cross_validation_table_1_chrom"][chrom]
        for i in range(len(table_1)):
            table_1[i][0] = tex_inline_math(table_1[i][0])
        table_1 = create_tabular(
            template=tabular_template,
            header=header_table_1,
            col_align=["c", "r", "r"],
            data=table_1,
        )

        # Getting the table 2
        table_2 = run_information["cross_validation_table_2_chrom"][chrom]
        for i in range(len(table_2)):
            table_2[i][0] = tex_inline_math(
                table_2[i][0].replace(">=", r"\geq "),
            )
        table_2 = create_tabular(
            template=tabular_template,
            header=header_table_2,
            col_align=["c", "r", "r"],
            data=table_2,
        )

        # The number of genotypes
        nb_genotypes = run_information["cross_validation_nb_genotypes_chrom"]
        nb_genotypes = nb_genotypes[chrom]

        # Adding the float
        tables += create_float(
            template=float_template,
            float_type="table",
            caption=wrap_tex(sanitize_tex(
                "IMPUTE2's internal cross-validation for chromosome {}. "
                "Tables show the percentage of concordance between genotyped "
                "calls and imputed calls for {:,d} "
                "genotypes.".format(chrom, nb_genotypes)
            )),
            label="tab:cross_validation_chr_{}".format(chrom),
            placement="H",
            content=table_1 + r"\hfill" + table_2,
        )

    # Adding the table for all the autosomes (Table 1)
    table_1 = run_information["cross_validation_table_1"]
    for i in range(len(table_1)):
        table_1[i][0] = tex_inline_math(table_1[i][0])
    table_1 = create_tabular(template=tabular_template, header=header_table_1,
                             col_align=["c", "r", "r"], data=table_1)

    # Adding the table for all the autosomes (Table 2)
    table_2 = run_information["cross_validation_table_2"]
    for i in range(len(table_2)):
        table_2[i][0] = tex_inline_math(table_2[i][0].replace(">=", r"\geq "))
    table_2 = create_tabular(template=tabular_template, header=header_table_2,
                             col_align=["c", "r", "r"], data=table_2)

    # The number of genotypes
    nb_genotypes = run_information["cross_validation_final_nb_genotypes"]

    # Adding the float
    tables += "\n\n" + create_float(
        template=float_template,
        float_type="table",
        caption=wrap_tex(sanitize_tex(
            "IMPUTE2's internal cross-validation across the genome. Tables "
            "show the percentage of concordance between genotyped calls and "
            "imputed calls for {:,d} genotypes.".format(nb_genotypes)
        )),
        label="tab:cross_validation",
        placement="H",
        content=table_1 + r"\hfill" + table_2,
    )

    # Creating the cross-validation subsection
    cross_validation_content = section_template.render(
        section_name="Cross-validation",
        section_type="subsection",
        section_content=cross_validation.render(tables=tables),
        section_label="subsec:cross_validation",
    )

    # Creating the completion rate subsection
    completion_rate_content = section_template.render(
        section_name="Completion rate",
        section_type="subsection",
        section_content=completion_rate.render(**run_information),
        section_label="subsec:completion_rate",
    )

    # Do we have a frequency pie?
    frequency_float = ""
    if run_information["frequency_pie"] != "":
        frequency_float = create_float(
            template=float_template,
            float_type="figure",
            caption=wrap_tex(sanitize_tex(
                "Proportions of minor allele frequencies for imputed "
                "sites with a completion rate of {}% or "
                "more at a probability of {}% or "
                "more.".format(run_information["rate_threshold"],
                               run_information["prob_threshold"])
            )),
            label="fig:frequency_pie",
            placement="H",
            content=graphics_template.render(
                width=r"0.5\textwidth",
                path=run_information["frequency_pie"],
            ),
        )
    run_information["frequency_float"] = frequency_float

    # Creating the frequency subsection
    frequencies_content = section_template.render(
        section_name="Minor allele frequencies",
        section_type="subsection",
        section_content=frequencies.render(**run_information),
        section_label="subsec:maf",
    )

    # The final content
    content = (cross_validation_content + completion_rate_content +
               frequencies_content)

    return section_template.render(section_name="Results",
                                   section_type="section",
                                   section_content=content,
                                   section_label="sec:results")


def _generate_conclusions(templates, run_options, run_information):
    """Generates the background section of the report.

    Args:
        templates (jinja2.Environment): the jinja2 template environment
        run_options (dict): the run options
        run_information (dict): the run information

    Returns:
        str: a string representation of the "conclusions" section

    """
    # Some assertions
    required_variables = ["nb_good_sites", "prob_threshold", "rate_threshold",
                          "info_threshold", "nb_genotyped"]
    for required_variable in required_variables:
        assert required_variable in run_information

    # Loading the template
    section_template = templates.get_template("section_template.tex")
    conclusions = templates.get_template("parts/conclusions.tex")
    itemize_template = templates.get_template("iterate_template.tex")

    # Adding the required information (output directories)
    run_information["output_dir"] = sanitize_tex(run_options.out_dir)
    run_information["output_dir_chrom"] = sanitize_tex(
        os.path.join(run_options.out_dir, "chr*")
    )
    run_information["output_final_impute2"] = sanitize_tex(
        os.path.join(run_options.out_dir, "chr*", "final_impute2")
    )

    # Output files
    output_files = [
        wrap_tex(
            format_tex(sanitize_tex("chr*.imputed.alleles"), "texttt") +
            sanitize_tex(": description of the reference and alternative "
                         "allele at each site.")
        ),
        wrap_tex(
            format_tex(sanitize_tex("chr*.imputed.completion_rates"),
                       "texttt") +
            sanitize_tex(": number of missing values and completion rate for "
                         "all site (using a probability threshold ") +
            tex_inline_math(
                r"\geq {}\%".format(run_information["prob_threshold"])
            ) + ")."
        ),
        wrap_tex(
            format_tex(sanitize_tex("chr*.imputed.good_sites"), "texttt") +
            sanitize_tex(": list of sites which pass the information "
                         "threshold (") +
            tex_inline_math(
                r"\geq {}".format(run_information["info_threshold"])
            ) + sanitize_tex(") and the completion rate threshold (") +
            tex_inline_math(
                r"\geq {}\%".format(run_information["rate_threshold"])
            ) + sanitize_tex(") using the probability threshold ") +
            tex_inline_math(
                r"\geq {}\%".format(run_information["prob_threshold"])
            ) + "."
        ),
        wrap_tex(
            format_tex(sanitize_tex("chr*.imputed.impute2"), "texttt") +
            sanitize_tex(": imputation results (merged from all segments).")
        ),
        wrap_tex(
            format_tex(sanitize_tex("chr*.imputed.impute2_info"), "texttt") +
            sanitize_tex(": the IMPUTE2 marker-wise information file (merged "
                         "from all segments).")
        ),
        wrap_tex(
            format_tex(sanitize_tex("chr*.imputed.imputed_sites"), "texttt") +
            sanitize_tex(": list of imputed sites (excluding sites that were "
                         "previously genotyped in the study cohort).")
        ),
        wrap_tex(
            format_tex(sanitize_tex("chr*.imputed.log"), "texttt") +
            sanitize_tex(": log file of the merging procedure.")
        ),
        wrap_tex(
            format_tex(sanitize_tex("chr*.imputed.maf"), "texttt") +
            sanitize_tex(": minor allele frequency (along with minor allele "
                         "identification) for all sites using the probability "
                         "threshold ") +
            tex_inline_math(
                r"\geq {}\%".format(run_information["prob_threshold"])
            ) + "."
        ),
        wrap_tex(
            format_tex(sanitize_tex("chr*.imputed.map"), "texttt") +
            sanitize_tex(": a map file describing the genomic location of "
                         "all sites.")
        ),
        wrap_tex(
            format_tex(sanitize_tex("chr*.imputed.sample"), "texttt") +
            sanitize_tex(": the sample file generated by the phasing step.")
        ),
    ]

    # Formating the enumeration of files
    run_information["output_files"] = itemize_template.render(
        iteration_type="itemize",
        iteration_list=output_files,
    )

    # Returning the section
    return section_template.render(
        section_name="Conclusions",
        section_type="section",
        section_label="sec:conclusions",
        section_content=conclusions.render(**run_information),
    )


def _generate_annex(templates, run_options, run_information):
    """Generates the annex section of the report (execution times).

    Args:
        templates (jinja2.Environment): the jinja2 template environment
        run_options (dict): the run options
        run_information (dict): the run information

    Returns:
        str: a string representation of the "Annex" section

    """
    # Some assertions
    required_variables = ["plink_exclude_exec_time",
                          "shapeit_check_1_exec_time",
                          "shapeit_check_2_exec_time",
                          "plink_missing_exec_time", "plink_flip_exec_time",
                          "plink_final_exec_time", "shapeit_phase_exec_time",
                          "merge_impute2_exec_time", "impute2_exec_time",
                          "bgzip_exec_time"]
    for required_variable in required_variables:
        assert required_variable in run_information, required_variable

    # Loading the templates
    tabular_template = templates.get_template("tabular_template.tex")
    float_template = templates.get_template("float_template.tex")

    # This section content
    content = ("The following tables show the execution time required by all "
               "the different tasks. All tasks are split by chromosomes. "
               "Execution times for imputation for each chromosome are means "
               "of individual segment times. Computing all genotyped markers' "
               "missing rate took {}.")
    content = wrap_tex(sanitize_tex(content.format(format_time(
        run_information["plink_missing_exec_time"],
        written_time=True,
    ))))

    # The header of the tables
    table_header = [
        format_tex(sanitize_tex("Chrom"), "textbf"),
        format_tex(sanitize_tex("Time"), "textbf"),
    ]

    # Getting the first table (plink_exclude_chr*)
    content += "\n\n" + _generate_time_float(
        table=run_information["plink_exclude_exec_time"],
        header=table_header,
        task_name="plink_exclude_chr*",
        label="plink_exclude_exec_time",
        tabular_t=tabular_template,
        float_t=float_template,
    )

    # Getting the second table (shapeit_check_chr*_1)
    content += _generate_time_float(
        table=run_information["shapeit_check_1_exec_time"],
        header=table_header,
        task_name="shapeit_check_chr*_1",
        label="shapeit_check_1_exec_time",
        tabular_t=tabular_template,
        float_t=float_template,
    )

    # Getting the third table (plink_flip_chr*)
    content += _generate_time_float(
        table=run_information["plink_flip_exec_time"],
        header=table_header,
        task_name="plink_flip_chr*",
        label="plink_flip_exec_time",
        tabular_t=tabular_template,
        float_t=float_template,
    )

    # Getting the fourth table (shapeit_check_chr*_2)
    content += _generate_time_float(
        table=run_information["shapeit_check_2_exec_time"],
        header=table_header,
        task_name="shapeit_check_chr*_2",
        label="shapeit_check_2_exec_time",
        tabular_t=tabular_template,
        float_t=float_template,
    )

    # Getting the fifth table (plink_final_exclude_chr*)
    content += _generate_time_float(
        table=run_information["plink_final_exec_time"],
        header=table_header,
        task_name="plink_final_exclude_chr*",
        label="plink_final_exclude_exec_time",
        tabular_t=tabular_template,
        float_t=float_template,
    )

    # Getting the sixth table (shapeit_phase_chr*)
    content += _generate_time_float(
        table=run_information["shapeit_phase_exec_time"],
        header=table_header,
        task_name="shapeit_phase_chr*",
        label="shapeit_phase_exec_time",
        tabular_t=tabular_template,
        float_t=float_template,
    )

    # Getting the seventh table (impute2_chr*)
    content += _generate_time_float(
        table=run_information["impute2_exec_time"],
        header=[format_tex(sanitize_tex("Chrom"), "textbf"),
                format_tex(sanitize_tex("Nb Seg."), "textbf"),
                format_tex(sanitize_tex("Mean T."), "textbf"),
                format_tex(sanitize_tex("Max T."), "textbf")],
        task_name="impute2_chr*",
        label="impute2_exec_time",
        tabular_t=tabular_template,
        float_t=float_template,
        first_time_col=2,
    )

    # Getting the eight table (merge_impute2_chr*)
    content += _generate_time_float(
        table=run_information["merge_impute2_exec_time"],
        header=table_header,
        task_name="merge_impute2_chr*",
        label="merge_impute2_exec_time",
        tabular_t=tabular_template,
        float_t=float_template,
    )

    # The last table (bgzip_chr*) only if present
    if run_information["bgzip_exec_time"]:
        content += _generate_time_float(
            table=run_information["bgzip_exec_time"],
            header=table_header,
            task_name="bgzip_chr*",
            label="bgzip_exec_time",
            tabular_t=tabular_template,
            float_t=float_template,
        )

    return content


def _generate_time_float(task_name, label, table, header, tabular_t, float_t,
                         first_time_col=1):
    """Generates time tables (split one long table in two).

    Args:
        task_name (str): the name of the task
        label (str): the label for the float
        table (list): the data for the float
        header (str): the header for the tables
        tabular_t (jinja2.Template): the template for the tabular
        float_t (jinja2.Template): the template for the float
        first_time_col (int): the first column containing time (base 0)

    Returns:
        str: a LaTeX float

    """
    assert len(table) == 22

    # Adding the first table
    table_1 = create_tabular(template=tabular_t, header=header,
                             col_align=["r"] * len(header),
                             data=_format_time_columns(table[:11],
                                                       first_time_col))

    # Adding the second table
    table_2 = create_tabular(template=tabular_t, header=header,
                             col_align=["r"] * len(header),
                             data=_format_time_columns(table[11:],
                                                       first_time_col))

    # The caption
    caption = sanitize_tex("Execution time for the '")
    caption += format_tex(sanitize_tex(task_name), "texttt")
    caption += sanitize_tex("' tasks.")

    # Returning the float
    return create_float(
        template=float_t,
        float_type="table",
        caption=wrap_tex(caption),
        label="tab:{}".format(label),
        placement="H",
        content=table_1 + r"\hspace{1cm}" + table_2,
    )


def _format_time_columns(table, first_col):
    """Colorize the time in the table (columns 2 and up).

    Args:
        table (list): the data for the tabular
        first_col (int): the first column containing time

    Returns:
        list: the same data, but with time column colorized

    """
    for i in range(len(table)):
        for j in range(first_col, len(table[i])):
            table[i][j] = colorize_time(table[i][j])
    return table
