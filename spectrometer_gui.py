import tkinter as tk
from tkinter import messagebox
from pylablib.devices.Andor import ShamrockSpectrograph

class SpectrometerGUI:
    def __init__(self, root):
        """
        Initialize the GUI and connect to the spectrometer.
        """
        self.root = root
        self.root.title("Andor Shamrock Spectrometer Control")

        # Connect to the spectrometer
        try:
            self.spectrometer = ShamrockSpectrograph()  # Automatically detect the device
            messagebox.showinfo("Connection Successful", "Spectrometer connected successfully!")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to the spectrometer: {e}")
            self.root.destroy()
            return

        # GUI Elements
        self.label = tk.Label(root, text="Center Wavelength (nm):")
        self.label.pack()

        self.entry = tk.Entry(root)
        self.entry.pack()

        self.set_wavelength_button = tk.Button(root, text="Set Wavelength", command=self.set_wavelength)
        self.set_wavelength_button.pack()

        self.read_wavelength_button = tk.Button(root, text="Read Wavelength", command=self.read_wavelength)
        self.read_wavelength_button.pack()

        self.response_label = tk.Label(root, text="Spectrometer Response:")
        self.response_label.pack()

        self.response_text = tk.Text(root, height=10, width=50)
        self.response_text.pack()

        # Button to close the connection
        self.close_button = tk.Button(root, text="Close Connection", command=self.close_connection)
        self.close_button.pack()

    def set_wavelength(self):
        """
        Set the center wavelength of the spectrometer.
        """
        try:
            wavelength = float(self.entry.get())
            self.spectrometer.set_center_wavelength(wavelength)
            self.response_text.insert(tk.END, f"Wavelength set to {wavelength} nm\n")
        except Exception as e:
            messagebox.showerror("Error", f"Error setting wavelength: {e}")

    def read_wavelength(self):
        """
        Read the current center wavelength from the spectrometer.
        """
        try:
            wavelength = self.spectrometer.get_center_wavelength()
            self.response_text.insert(tk.END, f"Current wavelength: {wavelength} nm\n")
        except Exception as e:
            messagebox.showerror("Error", f"Error reading wavelength: {e}")

    def close_connection(self):
        """
        Close the connection to the spectrometer.
        """
        try:
            self.spectrometer.close()
            messagebox.showinfo("Disconnected", "Spectrometer connection closed.")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Error closing connection: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SpectrometerGUI(root)
    root.mainloop()