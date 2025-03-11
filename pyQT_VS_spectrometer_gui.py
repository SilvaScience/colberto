import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QComboBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class SpectrometerGUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Spectrometer Experiment Metadata")

        # Layout
        self.layout = QVBoxLayout()

        # Wavelength Input
        self.wavelength_entry = QLineEdit(self)
        self.wavelength_entry.setFont(QFont('Arial', 16))  # Increased font size for input
        self.wavelength_entry.setFixedHeight(50)  # Increased height of the input box
        self.layout.addWidget(QLabel("Center Wavelength (nm):"))
        self.layout.addWidget(self.wavelength_entry)

        # Spectrometer Selection (Dropdown)
        self.spectrometer_combo = QComboBox(self)
        self.spectrometer_combo.addItem("Shamrock 750")  # Add the Shamrock 750 to the list
        self.spectrometer_combo.setFont(QFont('Arial', 16))  # Increased font size for dropdown
        self.layout.addWidget(QLabel("Select Spectrometer:"))
        self.layout.addWidget(self.spectrometer_combo)

        # Increase label font size
        label_font = QFont('Arial', 16)  # Larger font for labels
        self.layout.itemAt(0).widget().setFont(label_font)  # "Center Wavelength"
        self.layout.itemAt(2).widget().setFont(label_font)  # "Select Spectrometer"

        # Set layout
        self.setLayout(self.layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpectrometerGUI()
    window.show()
    sys.exit(app.exec_())
