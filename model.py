from transformers import VisionEncoderDecoderModel, TrOCRProcessor

# Specify the model name
model_name = "microsoft/trocr-base-printed"

# Load and save the processor and model
processor = TrOCRProcessor.from_pretrained(model_name)
model = VisionEncoderDecoderModel.from_pretrained(model_name)

# Save locally
processor.save_pretrained("./trocr_model")
model.save_pretrained("./trocr_model")


