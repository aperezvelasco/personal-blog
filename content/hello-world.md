---
title: Welcome to my Personal Site & AI Geoscience Hub
summary: Welcome to my new personal portfolio and blog. In this post, I introduce the website design, outline my professional background, and explain how the automated weekly AI geoscience paper aggregator works.
date: 2026-05-27
category: Blog
authors:
  - Antonio Pérez Velasco
---

Welcome to my personal site and blog! This space serves as both my professional portfolio and a hub for keeping track of the rapid developments at the intersection of **Artificial Intelligence (AI)** and the **Geosciences**.

## Why this site?

As a Senior Software and Data Engineer at [Predictia](http://www.predictia.es/), I spend my days building robust pipelines for climate data workflows, orchestrating containerized services in operational environments, and building deep learning models for meteorology. Climate data is inherently large, complex, and high-dimensional (working with NetCDF, GRIB, and Zarr formats).

In recent years, the integration of Machine Learning (ML) in weather and climate modeling has exploded. Models like _AIFS_ (ECMWF), _FourCastNet_, _GraphCast_, and various regional emulators are transforming how we predict weather and assess climate projections.

Keeping up with these papers can be overwhelming. To address this, I built an automated aggregator into this blog.

## How the Paper Aggregator Works

Every week, an automated script queries the public **arXiv API** for papers matching specific machine learning search terms in five key domains:

1. **Global & Regional Weather Forecasting**
2. **Subseasonal to Seasonal (S2S) Forecasting**
3. **Climate Emulation**
4. **Data Assimilation**
5. **Downscaling**

The fetched papers are categorized, merged with any manual blog posts I write, and updated directly on this page. You can filter posts using the tags in the blog section.

## Open Source & Collaboration

I'm a big believer in open science and open source. Many of my research topics and codebases are hosted publicly. For instance:

- **aq-biascorrection**: Bias correction of CAMS air quality forecasts using PyTorch. [GitHub Repo](https://github.com/ECMWFCode4Earth/aq-biascorrection)
- **DeepR**: Regional downscaling of global reanalysis datasets. [GitHub Repo](https://github.com/ECMWFCode4Earth/DeepR)

Feel free to look around, explore the papers, and get in touch if you have any questions or collaborations in mind!
