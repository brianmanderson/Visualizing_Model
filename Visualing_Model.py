import keras.backend as K
import numpy as np
import os
import matplotlib.pyplot as plt
from keras.models import Model

class visualization_model_class(object):
    def __init__(self, model,desired_layer_names=None, save_images=False):
        self.save_images = save_images
        self.out_path = None
        all_layers = model.layers[:]
        all_layers = [layer for layer in all_layers if layer.name.find('mask') == -1 and
                      layer.name.lower().find('input') == -1 and
                      layer.name.lower().find('batch_normalization') == -1 and
                      layer.name.lower().find('activation') == -1]
        if desired_layer_names:
            all_layers = [layer for layer in all_layers if layer.name in desired_layer_names]
        self.layer_outputs = [layer.output for layer in all_layers]  # We already have the input.
        self.layer_names = [layer.name for layer in all_layers]  #
        self.activation_model = Model(inputs=model.input, outputs=self.layer_outputs)

    def predict_on_tensor(self, img_tensor):
        self.activations = self.activation_model.predict(img_tensor)

    def define_output(self,out_path):
        self.out_path = out_path
        if not os.path.exists(self.out_path):
            os.makedirs(self.out_path)

    def plot_activations(self):
        if not self.out_path and self.save_images:
            self.define_output(os.path.join('.','activation_outputs'))
        image_index = 0
        print(self.layer_names)
        for layer_name, layer_activation in zip(self.layer_names, self.activations):
            print(layer_name)
            print(self.layer_names.index(layer_name) / len(self.layer_names) * 100)
            layer_activation = np.squeeze(layer_activation)
            display_grid = make_grid_from_map(layer_activation)
            scale = 0.05
            plt.figure(figsize=(display_grid.shape[1] * scale, scale * display_grid.shape[0]))
            plt.title(layer_name)
            plt.grid(False)
            plt.imshow(display_grid, aspect='auto', cmap='gray')
            if self.save_images:
                plt.savefig(os.path.join(self.out_path, str(image_index) + '_' + layer_name + '.png'))
                plt.close()
            image_index += 1


    def plot_kernels(self):
        if not self.out_path and self.save_images:
            self.define_output(os.path.join('.','kernel_outputs'))
        image_index = 0
        print(self.layer_names)
        for layer_name in self.layer_names:
            print(layer_name)
            print(self.layer_names.index(layer_name) / len(self.layer_names) * 100)
            kernels = np.squeeze(self.activation_model.layers[self.layer_names.index(layer_name)].get_weights()[0])
            display_grid = make_grid_from_map(kernels)
            scale = 0.05
            plt.figure(figsize=(display_grid.shape[1] * scale, scale * display_grid.shape[0]))
            plt.title(layer_name)
            plt.grid(False)
            plt.imshow(display_grid, aspect='auto', cmap='gray')
            if self.save_images:
                plt.savefig(os.path.join(self.out_path, str(image_index) + '_' + layer_name + '.png'))
                plt.close()
            image_index += 1

def visualize_activations(model, img_tensor, out_path = os.path.join('.','activation_outputs')):
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    all_layers = model.layers[1:]
    all_layers = [layer for layer in all_layers if layer.name.find('mask') == -1 and layer.name.lower().find('input') == -1 and layer.name.lower().find('batch_normalization') == -1]
    layer_outputs = [layer.output for layer in all_layers]  # We already have the input.
    layer_names = [layer.name for layer in all_layers]
    activation_model = Model(inputs=model.input, outputs=layer_outputs)
    activations = activation_model.predict(img_tensor)
    image_index = 0
    for layer_name, layer_activation in zip(layer_names, activations):
        print(layer_name)
        print(layer_names.index(layer_name)/len(layer_names) * 100)
        layer_activation = np.squeeze(layer_activation)
        display_grid = make_grid_from_map(layer_activation)
        scale = 0.05
        plt.figure(figsize=(display_grid.shape[1] * scale, scale * display_grid.shape[0]))
        plt.title(layer_name)
        plt.grid(False)
        plt.imshow(display_grid, aspect='auto', cmap='gray')
        plt.savefig(os.path.join(out_path,str(image_index) + '_' + layer_name + '.png'))
        plt.close()
        image_index += 1

def make_grid_from_map(layer_activation):
    n_features = layer_activation.shape[-1]
    split = 2
    while n_features / split % 2 == 0 and n_features / split >= split:
        split *= 2
    split /= 2
    images_per_row = int(n_features // split)
    if len(layer_activation.shape) == 4:
        rows_size = layer_activation.shape[1]
        cols_size = layer_activation.shape[2]
    else:
        rows_size = layer_activation.shape[0]
        cols_size = layer_activation.shape[1]
    n_cols = n_features // images_per_row
    display_grid = np.zeros((rows_size * images_per_row, n_cols * cols_size))
    for col in range(n_cols):
        for row in range(images_per_row):
            if len(layer_activation.shape) == 4:
                channel_image = layer_activation[layer_activation.shape[0] // 2, :, :, col * images_per_row + row]
            else:
                channel_image = layer_activation[:, :, col * images_per_row + row]
            channel_image -= channel_image.mean()
            channel_image /= channel_image.std()
            channel_image *= 64
            channel_image += 128
            channel_image = np.clip(channel_image, 0, 255).astype('uint8')
            display_grid[row * rows_size: (row + 1) * rows_size,
            col * cols_size: (col + 1) * cols_size] = channel_image
    return display_grid


def decay_regularization(img, grads, decay = 0.9):
    return decay * img


def clip_weak_pixel_regularization(img, grads, percentile = 1):
    clipped = img
    threshold = np.percentile(np.abs(img), percentile)
    clipped[np.where(np.abs(img) < threshold)] = 0
    return clipped


def gradient_ascent_iteration(loss_function, img):
    loss_value, grads_value = loss_function([img])
    gradient_ascent_step = img + grads_value * 0.9

    # Convert to row major format for using opencv routines
    grads_row_major = np.transpose(grads_value[0, :], (1, 2, 0))
    img_row_major = np.transpose(gradient_ascent_step[0, :], (1, 2, 0))

    # List of regularization functions to use
    regularizations = [decay_regularization, clip_weak_pixel_regularization]

    # The reguarlization weights
    weights = np.float32([3, 3, 1])
    weights /= np.sum(weights)

    images = [reg_func(img_row_major, grads_row_major) for reg_func in regularizations]
    weighted_images = np.float32([w * image for w, image in zip(weights, images)])
    img = np.sum(weighted_images, axis = 0)

    # Convert image back to 1 x 3 x height x width
    img = np.float32([np.transpose(img, (2, 0, 1))])

    return img


def deprocess_image(x):
    x -= x.mean()
    x /= (x.std() + 1e-5)
    x *= 0.1
    x += 0.5
    x = np.clip(x, 0, 1)
    x *= 255
    x = np.clip(x, 0, 255).astype('uint8')
    return x


def generate_pattern(model, layer_name, filter_index, size=150):
    layer_output = model.get_layer(layer_name).output
    loss = K.mean(layer_output[..., filter_index])
    grads = K.gradients(loss, model.input)[0]
    grads /= (K.sqrt(K.mean(K.square(grads))) + 1e-5)
    iterate = K.function([model.input], [loss, grads])
    img = np.random.random((1, size, size, 3)) * 20 + 128.
    for i in range(30):
        img = gradient_ascent_iteration(iterate, img)
    return deprocess_image(img[0])


def visualize_filters(model):
    layer_name = 'block1_conv1'
    size = 64
    margin = 5
    results = np.zeros((8 * size + 7 * margin, 8 * size + 7 * margin, 3) ,dtype='uint8')
    for i in range(8):
        print(i)
        for j in range(8):
            filter_img = generate_pattern(model, layer_name, i + (j * 8), size=size)
            horizontal_start = i * size + i * margin
            horizontal_end = horizontal_start + size
            vertical_start = j * size + j * margin
            vertical_end = vertical_start + size
            results[horizontal_start: horizontal_end, vertical_start: vertical_end, :] = filter_img
    plt.figure(figsize=(20, 20))
    plt.imshow(results)
