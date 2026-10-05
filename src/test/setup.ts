import "@testing-library/jest-dom";

// Test suites exercise the metric chain on fixtures without a real DEM/GCP
// reference: opt the spawned Python processes into the labelled synthetic
// dev calibration ("synthetic-dev-ref"). The shipped app never sets this.
process.env.DW_DEV_CALIBRATION = "1";
