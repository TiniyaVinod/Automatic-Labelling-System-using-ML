# Model For classification
import yolov5
import math


class model_class:
    def __init__(self, config):

        self.device = config["computing_device"]
        model_filename = config["model_filename"]

        if self.device == "cuda":  # If gpu is available
            self.model = yolov5.YOLOv5(model_filename, self.device)
        else:  # If gpu is NOT available
            self.model = yolov5.load(model_filename)

        self.default_config(config)

    def default_config(self, config):
        # set default value to parameters
        self.model.conf = config[
            "model_confidence_threshold"
        ]  # NMS confidence threshold
        self.model.iou = config["model_iou_threshold"]  # NMS IoU threshold
        self.model.agnostic = bool(config["model_agnostic"])  # NMS class-agnostic
        self.model.multi_label = bool(
            config["model_multi_label"]
        )  # NMS multiple labels per box
        self.model.max_det = config[
            "model_max_detection"
        ]  # maximum number of detections per image

    # Change parameter by selection
    # Set NMS confidence threshold
    def conf_threshold(self, conf_num):
        self.model.conf = conf_num

    # Set NMS IoU threshold
    def iou_threshold(self, iou_num):
        self.model.iou = iou_num

    # Set Maximum Detection
    def max_detection(self, det_num):
        self.model.max_det = det_num

    # Predict result
    def predict_result(self, img):

        if self.device == "cuda":  # if gpu is available
            result = self.model.predict(img)
            predictions = result.pred[0]
        else:  #  if gpu is NOT available
            result = self.model(img)
            output_result_text = []
            for i in range(len(result.pandas().xyxy[0].confidence)):
                output_result_text.append(
                    f"Class: {(result.pandas().xyxy[0].name[i]).upper()}, Confidence : {math.floor(result.pandas().xyxy[0].confidence[i]*100)} %"
                )
            if len(output_result_text) == 0:
                output_result_text.append("NO DETECTION!")
            predictions = result.pred[0]

            outputs_to_plot = []

            for i in range(len(result.pandas().xyxy[0].confidence)):
                obj_dict = {}
                obj_dict["label"] = result.pandas().xyxy[0].name[i]
                obj_dict["label_int"] = int(result.pandas().xyxy[0].get("class")[i])
                obj_dict["confidence"] = math.floor(
                    result.pandas().xyxy[0].confidence[i] * 100
                )
                obj_dict["x1"] = result.pandas().xyxy[0].xmin[i]
                obj_dict["y1"] = result.pandas().xyxy[0].ymin[i]
                obj_dict["x2"] = result.pandas().xyxy[0].xmax[i]
                obj_dict["y2"] = result.pandas().xyxy[0].ymax[i]
                outputs_to_plot.append(obj_dict)

        return (predictions, output_result_text, outputs_to_plot)
