"""
LSTM Autoencoder for multivariate time-series anomaly detection.

The core idea: train only on normal data. The model gets good at reconstructing
normal patterns. When something breaks, reconstruction error spikes. That spike
is your anomaly signal.

I tried a few architectures before landing here:
- Simple LSTM classifier: needs labeled anomaly data, which you rarely have enough of
- Isolation Forest: doesn't capture temporal dependencies at all
- Transformer: overkill for 60-step sequences, slower to train, no meaningful accuracy gain

The encoder-decoder with a bottleneck latent space forces the model to learn a
compressed representation of "normal". The decoder has to reconstruct from that
compressed form — if the input doesn't fit the learned normal distribution, it can't.
"""
import torch
import torch.nn as nn


class LSTMEncoder(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, latent_size: int):
        super().__init__()
        # dropout only applies between layers, not after the last one
        # that's why num_layers=1 triggers a warning — it's fine, just noisy
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hidden_size, latent_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, input_size)
        # we only care about the final hidden state — it summarizes the whole sequence
        _, (hidden, _) = self.lstm(x)
        return self.fc(hidden[-1])  # take last layer, shape: (batch, latent_size)


class LSTMDecoder(nn.Module):
    def __init__(self, latent_size: int, hidden_size: int, num_layers: int, output_size: int, seq_len: int):
        super().__init__()
        self.seq_len = seq_len
        self.fc = nn.Linear(latent_size, hidden_size)
        self.lstm = nn.LSTM(hidden_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.output_fc = nn.Linear(hidden_size, output_size)

    def forward(self, latent: torch.Tensor) -> torch.Tensor:
        # repeat the latent vector across the time dimension so the LSTM has
        # something to unroll from. not the only way to do this but it works.
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

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        """
        Per-sample MSE between input and reconstruction.
        Higher = more anomalous. Compare against threshold from train.py.

        Note: this runs under no_grad so it's safe to call in a hot path.
        Don't call model.train() before this — you want eval mode for consistent
        dropout behavior.
        """
        with torch.no_grad():
            recon = self.forward(x)
            return torch.mean((x - recon) ** 2, dim=(1, 2))
