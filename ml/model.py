"""LSTM Autoencoder for time-series anomaly detection."""
import torch
import torch.nn as nn


class LSTMEncoder(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, latent_size: int):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hidden_size, latent_size)

    def forward(self, x):
        # x: (batch, seq_len, input_size)
        _, (hidden, _) = self.lstm(x)
        # Take last layer hidden state
        latent = self.fc(hidden[-1])
        return latent


class LSTMDecoder(nn.Module):
    def __init__(self, latent_size: int, hidden_size: int, num_layers: int, output_size: int, seq_len: int):
        super().__init__()
        self.seq_len = seq_len
        self.fc = nn.Linear(latent_size, hidden_size)
        self.lstm = nn.LSTM(hidden_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.output_fc = nn.Linear(hidden_size, output_size)

    def forward(self, latent):
        # Expand latent to sequence
        x = self.fc(latent).unsqueeze(1).repeat(1, self.seq_len, 1)
        out, _ = self.lstm(x)
        return self.output_fc(out)


class LSTMAutoencoder(nn.Module):
    def __init__(
        self,
        input_size: int = 5,
        hidden_size: int = 64,
        num_layers: int = 2,
        latent_size: int = 16,
        seq_len: int = 60,
    ):
        super().__init__()
        self.encoder = LSTMEncoder(input_size, hidden_size, num_layers, latent_size)
        self.decoder = LSTMDecoder(latent_size, hidden_size, num_layers, input_size, seq_len)

    def forward(self, x):
        latent = self.encoder(x)
        reconstruction = self.decoder(latent)
        return reconstruction

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        """Returns per-sample MSE reconstruction error."""
        with torch.no_grad():
            recon = self.forward(x)
            error = torch.mean((x - recon) ** 2, dim=(1, 2))
        return error
