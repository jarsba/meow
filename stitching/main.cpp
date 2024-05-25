#include <pybind11/pybind11.h>
#include <pybind11/eigen.h>
#include "main.h"

namespace py = pybind11;
constexpr auto byref = py::return_value_policy::reference_internal;

PYBIND11_MODULE(SumLib, m) {
    m.doc() = "optional module docstring";

    py::class_<SumClass>(m, "SumClass")
    .def(py::init<double, double, int>())
    .def("run", &SumClass::run, py::call_guard<py::gil_scoped_release>())
    .def_readonly("sum", &SumClass::sum, byref)
    ;
}