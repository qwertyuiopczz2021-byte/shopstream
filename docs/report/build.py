
# -*- coding: utf-8 -*-
"""Builds ShopStream-Report.pdf from the modules in this folder."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import report_lib
import ch_intro
import ch_steps
import ch_cloud
import ch_end


def main():
    out = os.path.join(HERE, "ShopStream-Report.pdf")
    story = []
    b = report_lib.Builder(story)

    ch_intro.cover(b)
    ch_intro.front_matter(b)
    ch_intro.chapter1(b)
    ch_intro.chapter2(b)
    ch_steps.chapter3(b)
    ch_steps.chapter4(b)
    ch_steps.chapter5(b)
    ch_cloud.chapter6(b)
    ch_cloud.chapter7(b)
    ch_end.chapter8(b)
    ch_end.chapter9(b)
    ch_end.chapter10(b)
    ch_end.appendices(b)

    doc = report_lib.ReportDoc(out)
    doc.multiBuild(story)
    print(out)
    print("figures: %d, tables: %d" % (b.fig_n, b.tab_n))


if __name__ == "__main__":
    main()
